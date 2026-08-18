# Smart File Organizer

A command-line tool that organizes the files in a directory into
category subfolders based on file type — `Documents`, `Images`,
`Spreadsheets`, `Videos`, `Audio`, `Archives`, `Code`, and `Other`.

## Safety philosophy

File-moving tools are dangerous by nature, so this project is built
around three rules:

- **Dry-run is the default.** Running the tool without `--apply`
  never touches the filesystem — it only shows you what *would*
  happen.
- **Nothing moves without explicit confirmation.** Even with
  `--apply`, you must type `y` or `yes` at an interactive prompt
  after reviewing the full preview.
- **Existing files are never overwritten.** If a planned destination
  is already taken, a numbered alternative is used during planning
  (`report (1).pdf`), and if a destination unexpectedly becomes
  occupied between planning and execution, that individual move is
  skipped and reported as failed rather than overwriting anything.

## Installation

Requires Python 3.10+.

```bash
python -m pip install -e .
```

This installs the `smart-organizer` command.

## Development setup

Install with the `dev` extra to get `pytest`:

```bash
python -m pip install -e ".[dev]"
```

### Running tests

```bash
python -m pytest
```

All filesystem tests use pytest's `tmp_path` fixture — no test ever
touches a real directory on your machine.

## Usage

Preview only (default, makes no changes):

```bash
smart-organizer C:\Users\you\Downloads
```

Apply the changes (still requires confirmation):

```bash
smart-organizer C:\Users\you\Downloads --apply
```

`--apply` shows you the exact same preview first, then prompts:

```
Apply these changes? [y/N]:
```

Only `y` or `yes` (case-insensitive) proceeds. Anything else,
including just pressing Enter, cancels with no changes made.

## Supported categories

| Category      | Extensions                                                   |
|----------------|----------------------------------------------------------------|
| Documents      | `.pdf` `.doc` `.docx` `.txt` `.rtf`                            |
| Images         | `.jpg` `.jpeg` `.png` `.gif` `.webp`                           |
| Spreadsheets   | `.xlsx` `.xls` `.csv`                                          |
| Videos         | `.mp4` `.mov` `.avi` `.mkv`                                    |
| Audio          | `.mp3` `.wav` `.m4a`                                           |
| Archives       | `.zip` `.tar` `.gz` `.7z`                                      |
| Code           | `.py` `.js` `.ts` `.java` `.cpp` `.c` `.html` `.css` `.json`   |
| Other          | anything unrecognized, and files with no extension             |

Extension matching is case-insensitive (`PHOTO.JPG` is treated the
same as `photo.jpg`).

## Example

Before:

```
Downloads/
    report.pdf
    photo.jpg
    budget.xlsx
    mystery.xyz
```

After `smart-organizer Downloads --apply`:

```
Downloads/
    Documents/
        report.pdf
    Images/
        photo.jpg
    Spreadsheets/
        budget.xlsx
    Other/
        mystery.xyz
```

## Filename collisions

If a destination filename is already taken — either by a file
already on disk or by another file planned earlier in the same
run — a numbered suffix is appended: `report.pdf`, then
`report (1).pdf`, `report (2).pdf`, and so on, until a free name is
found. The original file is never overwritten.

## V1 limitations

- **Non-recursive**: only files directly inside the given directory
  are organized; subfolders and their contents are left alone.
- **Extension-based classification only**: category is decided
  purely by file extension, not file content.
- **No configuration file yet**: category rules are hard-coded.
- **No undo yet**: there is no built-in way to reverse a completed
  move, so review the dry-run preview carefully before using
  `--apply`.
