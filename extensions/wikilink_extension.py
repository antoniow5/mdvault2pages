from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as etree

from markdown.inlinepatterns import InlineProcessor
from markdown.extensions import Extension


class WikiLinkProcessor(InlineProcessor):

    def __init__(self, pattern, md, notes, vault):
        super().__init__(pattern, md)
        self.notes = notes
        self.vault = Path(vault).resolve()

    def handleMatch(self, m, data):
        # [[Note]] or ![[image.png]]
        target = m.group(1).strip()
        print(target)  # Debugging line

        is_image = target.startswith("!")

        if is_image:
            target = target[1:].strip()

        # Support [[Note|Display text]]
        # Support ![[image.png|300]]
        target = target[2:-2] if target.startswith("[[") and target.endswith("]]") else target
        if "|" in target:
            target, display = target.split("|", 1)
            target = target.strip()
            display = display.strip()
        else:
            display = ""

        if is_image:
            return self.render_image(
                target, display, m.start(0), m.end(0)
            )

        return self.render_link(
            target, display, m.start(0), m.end(0)
        )

    def render_image(self, target, display, start, end):
        allowed_extensions = {".jpg", ".jpeg", ".png", '.svg'}

        relative_path = Path(target)

        # Prevent absolute paths and directory traversal.
        if relative_path.is_absolute() or ".." in relative_path.parts:
            return self.broken_image(target, start, end)

        image_path = (self.vault / relative_path).resolve()

        try:
            image_path.relative_to(self.vault)
        except ValueError:
            return self.broken_image(target, start, end)

        if image_path.suffix.lower() not in allowed_extensions:
            return self.broken_image(target, start, end)

        if not image_path.is_file():
            return self.broken_image(target, start, end)

        url_path = image_path.relative_to(self.vault).as_posix()
        src = "/vault-files/" + quote(url_path, safe="/")

        element = etree.Element("img")
        element.set("src", src)
        element.set(
            "alt",
            image_path.stem if not display or display.isdigit() else display
        )
        element.set("loading", "lazy")
        element.set("class", "obsidian-image")

        # ![[image.png|300]] sets the image width.
        if display.isdigit():
            element.set("width", display)

        return element, start, end

    def broken_image(self, target, start, end):
        element = etree.Element("span")
        element.set("class", "broken-link")
        element.text = f"![[{target}]]"

        return element, start, end

    def render_link(self, target, display, start, end):
        target = target.strip().replace("\\", "/")

        if not target:
            return None, None, None

        # Allow [[folder/note]] and [[folder/note.md]].
        if target.endswith(".md"):
            target = target[:-3]

        target_path = Path(target)

        # Prevent absolute paths and directory traversal.
        if target_path.is_absolute() or ".." in target_path.parts:
            return self.broken_link(target, start, end)

        normalized_target = target_path.as_posix()
        print(f"Normalized target: {normalized_target}")  # Debugging line

        note = next(
            (
                note
                for note in self.notes
                if note.path.with_suffix("").as_posix() == normalized_target
            ),
            None,
        )
        
        if note is None:
            note = next(
                (
                    note
                    for note in self.notes
                    if note.name == normalized_target
                ),
                None,
            )

        if note is None:
            return self.broken_link(target, start, end)

        element = etree.Element("a")
        element.set(
            "href",
            "/note/" + quote(note.path.as_posix(), safe="/"),
        )
        element.text = display if display else note.name

        return element, start, end

    def broken_link(self, target, start, end):
        element = etree.Element("span")
        element.set("class", "broken-link")
        element.text = f"[[{target}]]"

        return element, start, end


class WikiLinkExtension(Extension):

    def __init__(self, notes, vault):
        self.notes = notes
        self.vault = Path(vault).resolve()
        super().__init__()

    def extendMarkdown(self, md):
        processor = WikiLinkProcessor(
            r"(!?\[\[([^\]]+)\]\])",
            md,
            self.notes,
            self.vault,
        )

        md.inlinePatterns.register(
            processor,
            "wikilink",
            175,
        )
