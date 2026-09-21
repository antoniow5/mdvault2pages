from markdown.inlinepatterns import InlineProcessor
from markdown.extensions import Extension
from xml.etree import ElementTree as etree


class WikiLinkProcessor(InlineProcessor):

    def __init__(self, pattern, md, notes):
        super().__init__(pattern, md)
        self.notes = notes

    def handleMatch(self, m, data):
        target = m.group(1).strip()

        # [[Note|Display text]]
        if "|" in target:
            note_name, display_text = target.split("|", 1)

            note_name = note_name.strip()
            display_text = display_text.strip()

        else:
            note_name = target
            display_text = target

        # Find the note
        note = next(
            (
                note
                for note in self.notes
                if note.name == note_name
            ),
            None
        )

        # Note doesn't exist
        if note is None:
            element = etree.Element("span")
            element.set("class", "broken-link")
            element.text = m.group(0)

            return (
                element,
                m.start(0),
                m.end(0)
            )

        element = etree.Element("a")

        element.set(
            "href",
            f"/note/{note.path}"
        )

        element.text = display_text

        return (
            element,
            m.start(0),
            m.end(0)
        )


class WikiLinkExtension(Extension):

    def __init__(self, notes):
        self.notes = notes
        super().__init__()

    def extendMarkdown(self, md):
        processor = WikiLinkProcessor(
            r"\[\[([^\]]+)\]\]",
            md,
            self.notes
        )

        md.inlinePatterns.register(
            processor,
            "wikilink",
            175
        )


