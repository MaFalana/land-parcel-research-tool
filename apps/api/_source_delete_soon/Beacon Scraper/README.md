# README

## Install Python dependencies.
It is recommended to use a virtual environment:

```
yo
python -m playwright install # playwright requires one extra step to download browser binaries
```

## Workflow summary:
1. The script loads your workbook and identifies columns according to the
header names.

2. For each row starting at row 3, it searches for the parcel number on the
Wells County Beacon site.

3. It clicks the Parcel Report link (if present), scrolls to the
Property Record Cards section, and identifies the newest PDF link
(typically labeled with the current year). If no record card exists for
the current year, it chooses the next most recent year.

4. The PDF is downloaded, temporarily saved, and parsed. The legal
description, latest deed date, and document identifier are extracted.

5. These values are written back into your workbook and saved after each row
to avoid losing progress.

6. The PDF file is renamed so that the _0 suffix is replaced with the
owner’s last name (common business suffixes such as LLC or INC are
ignored) and moved to the output directory.

7. If a “Downloaded” column exists, the cell for that row is set to TRUE.