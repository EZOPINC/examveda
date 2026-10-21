"""Create repeatable, development-only study-material navigation examples.

The command reuses the existing content taxonomy and page models. Stable slugs
make runs repeatable; conflicting editorial records stop the transaction
instead of being overwritten. It creates no exam attempts or scoring data.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from content.models import ContentPage, ExamCategory, ResourceMetadata, Subject


EXAMS = (
    ("wbpsc-clerkship", "WBPSC Clerkship", ("history", "general-studies", "mathematics")),
    ("wbcs", "WBCS", ("history", "geography", "general-studies")),
)

SUBJECTS = {
    "history": "History",
    "general-studies": "General Studies",
    "mathematics": "Mathematics",
    "geography": "Geography",
}

DEMO_NOTICE = (
    "DEMO RECORD — illustrative content only. This is not an authentic or "
    "verified official WBPSC previous-year paper. Questions and answers below "
    "were written as original placeholders for navigation testing."
)

QUESTION_SETS = {
    "history": {
        2023: (
            ("In this illustrative exercise, which source would most directly help a historian study an ancient ruler's public orders?", ("An inscription commissioned by the ruler", "A modern weather chart", "A present-day travel review", "A fictional story written centuries later"), 0, "An inscription can preserve a ruler's public orders."),
            ("A researcher compares two dated letters from the same period. Which skill is being practiced?", ("Source comparison", "Map projection", "Mental arithmetic", "Plant classification"), 0, "Comparing contemporary records is a basic historical method."),
            ("Which arrangement places these broad periods from earlier to later?", ("Ancient, medieval, modern", "Modern, ancient, medieval", "Medieval, modern, ancient", "Modern, medieval, ancient"), 0, "This is the conventional broad chronological order."),
        ),
        2022: (
            ("For a local-history study, which item is an example of a primary source?", ("A diary written during the event", "A recent summary article", "A classroom revision guide", "A modern novel inspired by the event"), 0, "A contemporary diary is a first-hand source."),
            ("A timeline helps a reader mainly to understand", ("the order of events over time", "the height of a mountain", "the area of a field", "the temperature of a river"), 0, "Timelines arrange events chronologically."),
            ("When two accounts disagree, a careful researcher should first", ("compare their dates, authors, and evidence", "discard both without review", "choose the longer account", "assume the newest account is always correct"), 0, "Source context and evidence help assess conflicting accounts."),
        ),
    },
    "general-studies": {
        2023: (
            ("In a fictional civic exercise, which body is described as making laws for a state?", ("The state legislature", "A local weather station", "A public library", "A sports association"), 0, "The state legislature is the law-making body at state level."),
            ("Which everyday action best supports water conservation?", ("Repairing a leaking tap", "Leaving a hose running", "Washing a few items under a constant stream", "Ignoring a broken pipe"), 0, "Repairing leaks prevents avoidable water loss."),
            ("A public notice should be written so that it is", ("clear and accessible to its intended readers", "intentionally ambiguous", "missing its date", "limited to unexplained abbreviations"), 0, "Clear wording helps readers understand public information."),
        ),
        2022: (
            ("Which source is most appropriate for checking a current municipal office schedule?", ("The municipality's official notice", "An undated anonymous message", "A fictional story", "A years-old personal note"), 0, "An official current notice is the most direct source."),
            ("The main purpose of a household budget is to", ("plan income and expenses", "measure rainfall", "record a map scale", "identify a rock type"), 0, "A budget helps organize income and spending."),
            ("Which practice makes a public meeting more inclusive?", ("Sharing the time and venue in advance", "Changing the venue without notice", "Restricting information to a few attendees", "Removing the agenda"), 0, "Advance notice gives people a fair chance to participate."),
        ),
    },
    "mathematics": {
        2023: (
            ("A notebook costs 80 units. After a 25% discount, what is its price?", ("60 units", "55 units", "65 units", "75 units"), 0, "25% of 80 is 20; 80 minus 20 is 60."),
            ("What is the mean of 4, 6, and 8?", ("6", "5", "7", "18"), 0, "The sum is 18, and 18 divided by 3 is 6."),
            ("A box contains 3 red and 2 blue counters. What fraction are blue?", ("2/5", "3/5", "1/2", "2/3"), 0, "There are 2 blue counters among 5 counters in total."),
        ),
        2022: (
            ("What is 15% of 200?", ("30", "15", "20", "45"), 0, "0.15 multiplied by 200 equals 30."),
            ("A 12-metre rope is cut into 4 equal lengths. How long is each piece?", ("3 metres", "4 metres", "8 metres", "48 metres"), 0, "12 divided by 4 equals 3."),
            ("A value rises from 40 to 50. By how much did it increase?", ("10", "5", "25", "90"), 0, "The difference is 50 minus 40, which equals 10."),
        ),
    },
    "geography": {
        2023: (
            ("On a standard map, which direction is usually at the top?", ("North", "South", "East", "West"), 0, "Most standard maps place north at the top unless a compass indicates otherwise."),
            ("A map scale is used to relate map distance to", ("distance on the ground", "air temperature", "population age", "river depth"), 0, "A scale represents the relationship between map and ground distances."),
            ("Which instrument is commonly used to show wind direction?", ("A wind vane", "A rain gauge", "A thermometer", "A measuring tape"), 0, "A wind vane indicates the direction from which wind blows."),
        ),
        2022: (
            ("Which feature is most directly represented by contour lines on a relief map?", ("Elevation and land shape", "Political party membership", "Daily exchange rates", "Road traffic noise"), 0, "Contour lines connect points of equal elevation."),
            ("If a river flows from higher land to lower land, its water moves", ("downhill under gravity", "toward every compass point equally", "only toward the equator", "without following the land"), 0, "Gravity drives surface water downhill."),
            ("Which of these is a renewable source of energy?", ("Sunlight", "Coal", "Petroleum", "Natural gas"), 0, "Sunlight is naturally replenished on a human timescale."),
        ),
    },
}


def _get_matching_record(model, lookup, expected, label):
    """Get a stable-key record or fail if it conflicts with existing content."""
    record, created = model.objects.get_or_create(**lookup, defaults=expected)
    if not created and any(getattr(record, field) != value for field, value in expected.items()):
        raise CommandError(f"Existing {label} {lookup!r} conflicts with the demo data; nothing was overwritten.")
    return record, created


def _format_question_body(subject_slug, year):
    """Build original, visibly illustrative questions for one demo paper."""
    subject_name = SUBJECTS[subject_slug]
    blocks = [DEMO_NOTICE, f"Illustrative {subject_name} questions — Demo Year {year}"]
    for number, (prompt, options, answer_index, explanation) in enumerate(QUESTION_SETS[subject_slug][year], start=1):
        blocks.append(f"{number}. {prompt}")
        blocks.extend(f"{letter}. {option}" for letter, option in zip("ABCD", options))
        blocks.append(f"Illustrative answer: {chr(65 + answer_index)}. {options[answer_index]} — {explanation}")
    return "\n\n".join(blocks)


class Command(BaseCommand):
    """Seed six exam/subject combinations and two published demo papers each."""

    help = "Create repeatable, clearly labelled local demo study materials."

    def handle(self, *args, **options):
        """Create missing rows atomically and refuse to run outside development."""
        if not settings.DEBUG:
            raise CommandError("Demo study materials may only be loaded with DEBUG=True development settings.")

        created = {"exams": 0, "subjects": 0, "papers": 0}
        now = timezone.now()
        with transaction.atomic():
            for exam_slug, exam_name, subject_slugs in EXAMS:
                category, was_created = _get_matching_record(
                    ExamCategory,
                    {"slug": exam_slug},
                    {"name": exam_name, "description": "", "is_active": True, "display_order": 0},
                    "exam",
                )
                created["exams"] += was_created
                for subject_slug in subject_slugs:
                    subject_name = SUBJECTS[subject_slug]
                    subject, was_created = _get_matching_record(
                        Subject,
                        {"slug": subject_slug},
                        {"name": subject_name, "description": "", "is_active": True},
                        "subject",
                    )
                    created["subjects"] += was_created
                    for year in (2023, 2022):
                        page_slug = f"demo-{exam_slug}-{subject_slug}-{year}-previous-question-paper"
                        title = f"DEMO — {exam_name} {subject_name} Previous-year Question Paper — Demo Year {year}"
                        summary = f"DEMO RECORD — illustrative content only; not an authentic or verified official {exam_name} paper."
                        body = _format_question_body(subject_slug, year)
                        page, was_created = _get_matching_record(
                            ContentPage,
                            {"slug": page_slug},
                            {
                                "title": title,
                                "summary": summary,
                                "body": body,
                                "language": ContentPage.Language.ENGLISH,
                                "is_published": True,
                                "seo_title": title,
                                "seo_description": summary,
                            },
                            "paper page",
                        )
                        if not was_created and (not page.published_at or page.published_at > now):
                            raise CommandError(f"Existing demo page {page_slug!r} has an invalid publication time.")
                        expected_metadata = {
                            "category": category,
                            "stage": None,
                            "year": year,
                            "resource_type": ResourceMetadata.ResourceType.PREVIOUS_QUESTIONS,
                            "subject": subject,
                            "topic": None,
                        }
                        metadata, metadata_created = ResourceMetadata.objects.get_or_create(
                            page=page,
                            defaults=expected_metadata,
                        )
                        if not metadata_created and any(
                            getattr(metadata, field) != value for field, value in expected_metadata.items()
                        ):
                            raise CommandError(f"Existing classification for {page_slug!r} conflicts with the demo data.")
                        created["papers"] += was_created

        self.stdout.write(self.style.SUCCESS(
            "Demo study materials ready: "
            f"{created['exams']} exams, {created['subjects']} subjects, {created['papers']} papers created."
        ))
