import os
import markdown

from dotenv import load_dotenv
from pathlib import Path
from dataclasses import dataclass

from flask import Flask, abort, render_template

from extensions.callout_extension import ObsidianCalloutsExtension
from extensions.wikilink_extension import WikiLinkExtension


load_dotenv()

VAULT = Path(os.environ["VAULT"])
INDEX_NOTE = VAULT / os.environ.get("INDEX_NOTE", "index.md")


@dataclass
class Note:
    name: str
    path: Path
    full_path: Path


def add_notes(vault: Path) -> list[Note]:
    notes = []

    for path in vault.rglob("*.md"):
        name = path.name.removesuffix(".md")

        notes.append(
            Note(
                name=name,
                path=path.relative_to(VAULT),
                full_path=path
            )
        )
    return notes




def build_tree(vault: Path, current_path: Path | None = None):
    def build_directory(path: Path):
        items = []

        directories = sorted(
            [p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")],
            key=lambda p: p.name.lower(),
        )

        files = sorted(
            [
                p for p in path.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".md"
                and not p.name.startswith(".")
            ],
            key=lambda p: p.name.lower(),
        )

        for directory in directories:
            items.append({
                "type": "directory",
                "name": directory.name,
                "children": build_directory(directory),
            })

        for file in files:
            items.append({
                "type": "file",
                "name": file.stem,
                "path": file.relative_to(VAULT),
                "active": current_path == file,
            })

        return items

    return build_directory(vault)


def get_note(path: Path, notes) -> Note | None:
    for note in notes:
        if note.path == path:
            return note
    return None


def render_note(note: Note, notes):
    path = Path(VAULT / note.path)
    if not path.exists():
        abort(404)

    text = path.read_text(
        encoding="utf-8"
    )

    md = markdown.Markdown(
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "toc",

            "nl2br",
            "pymdownx.arithmatex",
            WikiLinkExtension(notes),
            ObsidianCalloutsExtension(), 
        ],
        extension_configs={
        "toc": {
            "toc_depth": "2-6",
        },
        "pymdownx.arithmatex": {
            "generic": True,
        },
    }
    )

    content = md.convert(text)
    tree = build_tree(VAULT, path)

    return render_template(
        "note.html",
        content=content,
        toc=md.toc,
        note=note,
        tree=tree,
        has_toc = bool(md.toc_tokens)
    )


app = Flask(__name__)


@app.route("/")
def index():
    notes = add_notes(VAULT)

    note = get_note(Path('index.md'), notes)
    return render_note(note, notes)



@app.route("/note/<path:path>")
def note(path):
    note_path = Path(path)

    notes = add_notes(VAULT)

    note = get_note(note_path, notes)

    if not note:
        abort(404)
        return
    elif not note.full_path.is_file():
        abort(404)
        return
    return render_note(note, notes)




if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
