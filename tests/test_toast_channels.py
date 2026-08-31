"""The hide-and-reshow mechanism behind every replace-in-place toast channel.

These cover the helper itself: what one emission shows, what it hides, and what
it writes back to the per-client channel registry. The channel *assignments* --
which toast belongs to which lane -- live with the callbacks that emit them.
"""

from dash import no_update

from source.utilities import notifications
from source.utilities.notifications import channel_toast, toast


def _registry_operations(patch) -> list[tuple[str, list, object]]:
    """Read a ``dash.Patch`` as the (kind, location, value) it will apply."""
    return [
        (
            operation["operation"],
            operation["location"],
            operation["params"].get("value"),
        )
        for operation in patch._operations
    ]


def _registry_writes(patch) -> dict[str, str | None]:
    """Read a per-key ``dash.Patch`` as the assignments it will apply."""
    if patch is no_update:
        return {}
    return {
        location[0]: value for _kind, location, value in _registry_operations(patch)
    }


def _emit(channel_key: str, registry, *, clears=()):
    """Emit one channel toast with throwaway copy."""
    return channel_toast(
        toast(channel_key, "Title", "Message", color="red"),
        registry,
        clears=clears,
    )


def test_an_emission_shows_a_fresh_instance_under_the_channel_key():
    send, hide, patch = _emit("import-failed", {})

    (payload,) = send
    assert payload["id"].startswith("import-failed-")
    assert payload["id"] != "import-failed"
    assert payload["title"] == "Title"
    assert payload["action"] == "show"
    # Nothing on screen for this channel yet, so there is nothing to retire.
    assert hide == []
    assert _registry_writes(patch) == {"import-failed": payload["id"]}


def test_a_repeat_emission_hides_the_instance_it_replaces():
    first_send, _first_hide, first_patch = _emit("import-failed", {})
    registry = _registry_writes(first_patch)

    second_send, second_hide, second_patch = _emit("import-failed", registry)

    assert second_send[0]["id"] != first_send[0]["id"]
    assert second_hide == [first_send[0]["id"]]
    assert _registry_writes(second_patch) == {"import-failed": second_send[0]["id"]}


def test_distinct_channel_keys_do_not_hide_each_other():
    """The reported bug: two subjects in flight must stack, not swallow."""
    send_a, _hide_a, patch_a = _emit("import-successful-AAA", {})
    registry = _registry_writes(patch_a)

    send_b, hide_b, patch_b = _emit("import-successful-BBB", registry)

    assert hide_b == []
    assert send_b[0]["id"] != send_a[0]["id"]
    assert _registry_writes(patch_b) == {"import-successful-BBB": send_b[0]["id"]}


def test_a_success_also_hides_and_clears_the_channels_it_falsifies():
    _send, _hide, failure_patch = _emit("import-failed", {})
    registry = _registry_writes(failure_patch)

    send, hide, patch = _emit(
        "import-successful-AAA", registry, clears=("import-failed",)
    )

    assert hide == [registry["import-failed"]]
    assert _registry_writes(patch) == {
        "import-successful-AAA": send[0]["id"],
        "import-failed": None,
    }


def test_clearing_a_channel_with_nothing_on_screen_hides_nothing():
    """Hiding an absent id is a clean no-op, so an unfired lane costs nothing."""
    _send, hide, patch = _emit("cleanup-successful", {}, clears=("cleanup-failed",))

    assert hide == []
    assert _registry_writes(patch)["cleanup-failed"] is None


def test_a_cleared_channel_is_not_hidden_twice():
    _send, _hide, failure_patch = _emit("import-failed", {})
    registry = _registry_writes(failure_patch)
    _send, _hide, first_success = _emit(
        "import-successful-AAA", registry, clears=("import-failed",)
    )
    registry.update(_registry_writes(first_success))

    _send, hide, _patch = _emit(
        "import-successful-AAA", registry, clears=("import-failed",)
    )

    # Only the previous success instance: the failure was cleared out of the
    # registry when it was hidden.
    assert hide == [_registry_writes(first_success)["import-successful-AAA"]]


def test_every_registry_write_is_a_per_key_assignment():
    """Never a whole-dict replacement -- that is what makes interleaving safe."""
    _send, _hide, patch = _emit(
        "import-successful-AAA", {"unrelated": "unrelated-1"}, clears=("import-failed",)
    )

    operations = _registry_operations(patch)

    assert [kind for kind, _location, _value in operations] == ["Assign", "Assign"]
    assert [location for _kind, location, _value in operations] == [
        ["import-successful-AAA"],
        ["import-failed"],
    ]


def test_two_callbacks_landing_out_of_order_keep_both_entries():
    """The interleaving a whole-dict write would lose.

    Two callbacks read the same registry, emit on different channels, and their
    responses land in the reverse order. Each response assigns only its own
    keys, so neither can carry a stale value for the other's channel.
    """
    registry: dict[str, str | None] = {}
    send_a, _hide_a, patch_a = _emit("rank-refresh-problem", registry)
    send_b, _hide_b, patch_b = _emit("import-failed", registry)

    for patch in (patch_b, patch_a):
        registry.update(_registry_writes(patch))

    assert registry == {
        "rank-refresh-problem": send_a[0]["id"],
        "import-failed": send_b[0]["id"],
    }


def test_overlapping_emissions_of_one_channel_touch_only_that_key():
    """Two clicks of one action, both computed before either response applied.

    Which of the two wins is the renderer's call -- every channel has exactly
    one producing callback, and Dash discards an older in-flight invocation's
    response for the same output set. What the helper guarantees is that
    neither response can disturb any other channel, whichever order they land.
    """
    registry: dict[str, str | None] = {"run-verdict": "run-verdict-old"}
    _first_send, first_hide, first_patch = _emit("import-failed", registry)
    _second_send, second_hide, second_patch = _emit("import-failed", registry)

    for patch in (second_patch, first_patch):
        registry.update(_registry_writes(patch))

    assert first_hide == second_hide == []
    assert set(_registry_writes(first_patch)) == {"import-failed"}
    assert set(_registry_writes(second_patch)) == {"import-failed"}
    assert registry["run-verdict"] == "run-verdict-old"


def test_a_missing_registry_reads_as_an_empty_one():
    """A store that has never been written arrives as None, not a dict."""
    _send, hide, patch = _emit("import-failed", None)

    assert hide == []
    assert set(_registry_writes(patch)) == {"import-failed"}


def test_upsert_toast_is_gone():
    """One replacement mechanism app-wide (D3).

    The alternating-``autoClose`` upsert existed only to re-arm a replacement's
    timer under a reused id. Every channel now shows a fresh id instead, so the
    trick and its sequence store are deleted rather than kept for one toast.
    """
    assert not hasattr(notifications, "upsert_toast")
    assert not hasattr(notifications, "TOAST_LIFETIME_STORE_ID")
    # The sticky pairing survives: the celebration has no timer to re-arm.
    assert hasattr(notifications, "upsert_sticky_toast")
