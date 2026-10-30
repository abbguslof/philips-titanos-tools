# Firmware acquisition

Status: the package used for this research was acquired and parsed. This guide
does not host or redistribute vendor firmware.

## Find the support page for your model

The exact URL differs by model and region. For the research unit it was:

```text
https://www.philips.com/c-w/support-main/55pus8000_12.html
```

Open the page for **your** model and look for the software/firmware download
section. The support page is the authoritative source. Do not guess a firmware
for a different chassis.

## Helper tool

The same workflow is available as a careful helper:

```bash
python3 tools/firmware/fetch.py --model 55pus8000_12 --probe
```

It fetches the support page, extracts `download.p4c.philips.com` links, and
HEADs a small list of model/language filename candidates. It does not bypass
authentication or guess private URLs. Use `--download URL -o file` only with a
URL you have verified.

## Historical example: extract candidate download URLs

The research started by scraping the support page for `download.p4c.philips.com`
links:

```bash
curl -sL 'https://www.philips.com/c-w/support-main/55pus8000_12.html' \
  | grep -oE "https://download\.p4c\.philips\.com[^\"' ]+" \
  | sort -u
```

If the page does not expose a direct link, the firmware filename often follows a
model-and-language pattern. The historical probe was:

```bash
for f in 55pus8000_12_pkg_eng.zip 55pus8000_12_fw_eng.zip 55pus8000_12_pkg_tra.zip; do
  echo "== $f"
  curl -sIL "https://download.p4c.philips.com/files/5/$f" | head -5
done
```

Only use filenames that match the model and firmware branch you actually have
(`Main SW ID` in the TV's service menu). A wrong package can fail the update or
worse. Keep this to a handful of candidates; do not hammer the vendor server.

## Historical example: third-party mirror

The research unit's package was eventually fetched from a public Google Drive
mirror. The exact historical command was:

```bash
curl -sL --max-time 900 \
  "https://drive.usercontent.google.com/download?id=1ldiXYH7iKoA-bHfD9d9cyJyHxCpW4wFV&export=download&confirm=t" \
  -o TPN256E_056.002.236.191_upgrade.zip
```

**This mirror is third-party, not maintained by this project, and may disappear.**
The `upgrade_loader.bin` file in early notes is not a loader; it is the Google
Drive virus-scan warning HTML for that download. Prefer the official Philips
support page whenever it works.

## Recorded hashes for the research package

```text
file: TPN256E_056.002.236.191_upgrade.zip
size: 1504229364 bytes
md5:  0a24acc5b7a3c39b181957c4081e17f6
sha256: 0e5f2b454ae476263336b1d06447f13665645f9fd28bba92f5e259f772f5eea2

file: PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg
size: 1530220984 bytes
md5:  555c71b5a79c52da3dfcaa19f2cc2093
sha256: 7b6c7e14298f2845289aeeff500366dcb72be8e748999e44a3244a3a5b2344f3
```

Verify before extraction:

```bash
sha256sum TPN256E_056.002.236.191_upgrade.zip
unzip -l TPN256E_056.002.236.191_upgrade.zip | head
```

## What to do with the package

The zip contains the Novatek `.pkg`. See
[firmware extraction](firmware-extraction.md). Keep the package outside the
repository; `.gitignore` excludes `*.zip`, `*.pkg`, `fw/`, and extracted
filesystems.

## Legal and safety

- Download firmware only for hardware you own.
- Do not redistribute the vendor package from this repository.
- Keep a pristine copy and a known-good NVM/EDID backup before flashing.
- A package for another chassis/model can brick the TV. Match the `Main SW ID`.
