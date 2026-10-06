# Local icons

These files are the small set of icons used by the dashboard UI. They replace
runtime Iconify API requests so the local app keeps its chrome intact offline.

The SVGs were copied from Iconify icon records for these collections:

| Prefix | Collection | License |
| --- | --- | --- |
| `bi` | Bootstrap Icons | [MIT](https://github.com/twbs/icons/blob/main/LICENSE) |
| `clarity` | Clarity Icons | [MIT](https://github.com/vmware-clarity/core/blob/main/LICENSE) |
| `fontisto` | Fontisto | [MIT](https://github.com/kenangundogan/fontisto/blob/master/LICENSE) |
| `ion` | Ionicons | [MIT](https://github.com/ionic-team/ionicons/blob/main/LICENSE) |
| `logos` | SVG Logos | [CC0](https://github.com/gilbarbara/logos/blob/main/LICENSE.txt) |
| `material-symbols` | Material Symbols | [Apache 2.0](https://github.com/google/material-design-icons/blob/master/LICENSE) |
| `radix-icons` | Radix Icons | [MIT](https://github.com/radix-ui/icons/blob/master/LICENSE) |

When adding icons, vendor only the specific SVGs the app uses and confirm the
source collection's license before committing.

## Evxl's logo

`evxl-logo.png` is the one file here that is not from an icon collection and
is under no open license. It is the logo of [Evxl.app](https://evxl.app) and
belongs to Evxl's owner. The app shows it as the link from a benchmark's
scenario page to that benchmark on Evxl.

- **Permission.** Evxl's owner told this project's maintainer, in a direct
  message, that the app may use it, with no conditions. Recorded 2026-10-05.
  The message is private, so nothing here links to it.
- **Still the owner's.** The permission was given to this project. The
  repository's license does not cover the logo, and can't grant anyone a
  right to it.
- **The file.** The 721×679 `icon.png` the site serves, scaled down to
  102×96. Nothing else was changed. Recoloring or redrawing it needs the
  owner's say first.
- **Bundled.** Like the other icons it is served from this folder, and the
  app never requests it from evxl.app.
