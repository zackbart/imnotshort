# imnotshort

A single-page AR site for PowerPoint Night. Scan the QR, tap, point at the floor —
iOS AR Quick Look drops a 165 cm stick figure (global average human height) so the
audience can see I'm taller than it.

## Stack

- Static `public/` served by a tiny `Bun.serve` (`server.js`)
- USDZ generated procedurally from a Python script (`build/make_usdz.py`) using
  the system `usdzip` for proper 64-byte alignment
- iOS-only target (AR Quick Look)

## Develop

```sh
bun run dev          # hot reload, http://localhost:3000
bun run build:figure # regenerate public/figure.usdz
```

## Geometry

The stick figure is 1.65 m tall (5'5"). Tweak in `build/make_usdz.py`:

```py
build_usda(height=1.65)  # meters
```

Re-run `build:figure` after changes.

## Deploy

Railway (Railpack builder). See `railway.json`.
