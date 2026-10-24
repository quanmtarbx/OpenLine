# OpenLine Desk 0.3.1

OpenLine Desk is a Windows launcher and run-planning companion for OpenBVE. Its Drive page brings route/train selection and previews together, with separate pages for multiplayer sessions, content, settings, and help.

## Start it on Windows

1. Download and extract `OpenLineDesk-0.3.1-Windows.zip` to a normal folder (do not run it inside WinRAR's temporary preview).
2. Double-click `Start-OpenLine.bat`.
3. The starter uses installed Python with Tkinter. If none is available, it downloads a private Python runtime for OpenLine Desk.
4. In **Content**, choose the OpenBVE `Railway\Route` and `Train` folders. In **Settings**, choose `OpenBve.exe`.
5. On **Drive**, select a route and train and press **Start Duty in OpenBVE**.

Drive displays route and train PNG previews. It looks for route maps referenced by the route and preview images in the train folder. Use the PNG buttons to choose images manually when an add-on does not include a suitable preview.

## Multiplayer

The **Multiplayer** page detects the installed OBND OpenBVE Multiplayer build from its Windows install registration, checks for the multiplayer client and server files, and opens that build directly. The package at [the OBND multiplayer download](https://www.openbvenews.com/downloads/fetch/235) is an installer; after installing it, OpenLine can find the `OpenBve.exe` automatically. You can also browse to it manually (for example, `C:\Program Files (x86)\openBVE\OpenBve.exe`).

Hosting, joining, server selection, and synchronization are provided by the Multiplayer edition's built-in screen. OpenLine opens that screen without passing unsupported network command-line switches. Use **Copy run plan** to share the selected route, train, date, and time; choose those same route and train add-ons in the Multiplayer app before connecting. Standard OpenBVE remains single-player.

## Timetables and run options

OpenLine reads route timetable entries when present. OpenBVE creates the working timetable from route data. The launcher passes the selected route and train; run date, time, and service program are saved on the local run card because OpenBVE does not expose those as generic launch arguments.

The conductor companion provides a station list, spoken stop announcements, platform checklist, and activity log. It runs beside OpenBVE and does not control simulator doors or cameras.

## Updating OpenLine Desk

The app can check an HTTPS JSON manifest and install a newer `OpenLineDesk.py` without downloading the full ZIP. The included `.github/workflows/release.yml` publishes a ZIP, app script, and checksum manifest when a new `VERSION` is pushed to `main`. The released app uses the public update channel `https://github.com/quanmtarbx/OpenLine/releases/latest/download/update-manifest.json`. Pushing a version change to `main` publishes a matching `v*` release with a Windows ZIP, app script, and checksum manifest.

## References

- [openOMSI project](https://github.com/openOMSI-org/openOMSI)
- [openOMSI 0.3.37 release](https://github.com/openOMSI-org/openOMSI/releases/tag/v0.3.37)
- [OpenBVE multiplayer mod channel](https://www.openbvenews.com/multiplayer/)
- [OpenBVE 1.14.1.2 release](https://github.com/leezer3/OpenBVE/releases/tag/1.14.1.2)
- [OpenBVE CSV route format](https://openbve-project.net/documentation/HTML/route_csv.html)
