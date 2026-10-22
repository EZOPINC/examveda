"""Create one repeatable local mock test with complete en/hi/bn variants.

The command reuses exam_engine's production models and scoring rules. It is an
explicit DEBUG-only operation, refuses conflicting stable identifiers, and
never creates attempts or changes existing authored records.
"""

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Subject
from exam_engine.models import (
    MockTest,
    MockTestQuestion,
    MockTestTranslation,
    Question,
    QuestionOption,
    QuestionOptionTranslation,
    QuestionTranslation,
)


SUBJECT = {"name": "Demo Mock Test History", "slug": "demo-mock-test-history"}
TEST = {
    "title": "DEMO — WBPSC History Practice (English / हिन्दी / বাংলা)",
    "slug": "demo-wbpsc-multilingual-practice",
    "description": "Local demo test with five original illustrative questions; not an official or verified WBPSC paper.",
    "instructions": "This is a local demo. Select answers, save them, and submit to view the stored answer key and explanations.",
    "language": "en",
    "duration_minutes": 10,
    "is_published": True,
}
TEST_TRANSLATIONS = {
    "hi": {
        "title": "डेमो — WBPSC इतिहास अभ्यास",
        "description": "पाँच मौलिक उदाहरणात्मक प्रश्नों वाला स्थानीय डेमो टेस्ट; यह आधिकारिक या सत्यापित WBPSC प्रश्नपत्र नहीं है।",
        "instructions": "यह स्थानीय डेमो है। उत्तर चुनें, उन्हें सहेजें और जमा करने के बाद उत्तर-कुंजी तथा व्याख्याएँ देखें।",
    },
    "bn": {
        "title": "ডেমো — WBPSC ইতিহাস অনুশীলন",
        "description": "পাঁচটি মৌলিক উদাহরণমূলক প্রশ্নসহ স্থানীয় ডেমো পরীক্ষা; এটি কোনো সরকারি বা যাচাইকৃত WBPSC প্রশ্নপত্র নয়।",
        "instructions": "এটি একটি স্থানীয় ডেমো। উত্তর নির্বাচন করে সংরক্ষণ করুন এবং জমা দেওয়ার পরে উত্তরসূচি ও ব্যাখ্যা দেখুন।",
    },
}

# Each record contains source text, four stable-position options, correct index,
# explanation, and complete translations. Correctness is stored only once on
# QuestionOption, never on translation rows.
QUESTIONS = (
    {
        "prompt": "Which Indus Valley site is especially known for the Great Bath?",
        "explanation": "The Great Bath is a major public structure excavated at Mohenjo-daro.",
        "options": ("Mohenjo-daro", "Lothal", "Kalibangan", "Dholavira"),
        "correct": 0,
        "hi": {
            "prompt": "सिंधु घाटी का कौन-सा स्थल विशाल स्नानागार के लिए विशेष रूप से प्रसिद्ध है?",
            "explanation": "मोहनजोदड़ो में खुदाई के दौरान विशाल स्नानागार नामक प्रमुख सार्वजनिक संरचना मिली थी।",
            "options": ("मोहनजोदड़ो", "लोथल", "कालीबंगा", "धोलावीरा"),
        },
        "bn": {
            "prompt": "সিন্ধু সভ্যতার কোন স্থানটি বৃহৎ স্নানাগারের জন্য বিশেষভাবে পরিচিত?",
            "explanation": "মহেঞ্জোদারোতে খননের সময় বৃহৎ স্নানাগার নামে একটি গুরুত্বপূর্ণ জনসাধারণের স্থাপনা পাওয়া যায়।",
            "options": ("মহেঞ্জোদারো", "লোথাল", "কালিবঙ্গান", "ধোলাভিরা"),
        },
    },
    {
        "prompt": "Most of Emperor Ashoka's inscriptions were written in which language?",
        "explanation": "Many Ashokan edicts in the subcontinent use Prakrit, commonly written in Brahmi script.",
        "options": ("Prakrit", "Persian", "Tamil", "Greek"),
        "correct": 0,
        "hi": {
            "prompt": "सम्राट अशोक के अधिकांश अभिलेख किस भाषा में लिखे गए थे?",
            "explanation": "उपमहाद्वीप में अशोक के अनेक शिलालेख प्राकृत भाषा में हैं और सामान्यतः ब्राह्मी लिपि में लिखे गए हैं।",
            "options": ("प्राकृत", "फ़ारसी", "तमिल", "यूनानी"),
        },
        "bn": {
            "prompt": "সম্রাট অশোকের অধিকাংশ শিলালিপি কোন ভাষায় লেখা হয়েছিল?",
            "explanation": "উপমহাদেশে অশোকের বহু শিলালিপি প্রাকৃত ভাষায় এবং সাধারণত ব্রাহ্মী লিপিতে লেখা।",
            "options": ("প্রাকৃত", "ফারসি", "তামিল", "গ্রিক"),
        },
    },
    {
        "prompt": "In which year was the Indian National Congress founded?",
        "explanation": "The Indian National Congress was founded in 1885.",
        "options": ("1885", "1857", "1905", "1919"),
        "correct": 0,
        "hi": {
            "prompt": "भारतीय राष्ट्रीय कांग्रेस की स्थापना किस वर्ष हुई थी?",
            "explanation": "भारतीय राष्ट्रीय कांग्रेस की स्थापना 1885 में हुई थी।",
            "options": ("1885", "1857", "1905", "1919"),
        },
        "bn": {
            "prompt": "ভারতীয় জাতীয় কংগ্রেস কোন সালে প্রতিষ্ঠিত হয়েছিল?",
            "explanation": "ভারতীয় জাতীয় কংগ্রেস ১৮৮৫ সালে প্রতিষ্ঠিত হয়েছিল।",
            "options": ("১৮৮৫", "১৮৫৭", "১৯০৫", "১৯১৯"),
        },
    },
    {
        "prompt": "The Battle of Plassey took place in which year?",
        "explanation": "The Battle of Plassey was fought in 1757.",
        "options": ("1757", "1764", "1773", "1857"),
        "correct": 0,
        "hi": {
            "prompt": "प्लासी का युद्ध किस वर्ष हुआ था?",
            "explanation": "प्लासी का युद्ध 1757 में लड़ा गया था।",
            "options": ("1757", "1764", "1773", "1857"),
        },
        "bn": {
            "prompt": "পলাশীর যুদ্ধ কোন সালে হয়েছিল?",
            "explanation": "পলাশীর যুদ্ধ ১৭৫৭ সালে হয়েছিল।",
            "options": ("১৭৫৭", "১৭৬৪", "১৭৭৩", "১৮৫৭"),
        },
    },
    {
        "prompt": "Who introduced the Permanent Settlement in Bengal in 1793?",
        "explanation": "The Permanent Settlement was introduced under Governor-General Lord Cornwallis in 1793.",
        "options": ("Lord Cornwallis", "Warren Hastings", "Lord Dalhousie", "Robert Clive"),
        "correct": 0,
        "hi": {
            "prompt": "1793 में बंगाल में स्थायी बंदोबस्त किसने लागू किया था?",
            "explanation": "1793 में गवर्नर-जनरल लॉर्ड कॉर्नवालिस के शासनकाल में स्थायी बंदोबस्त लागू किया गया था।",
            "options": ("लॉर्ड कॉर्नवालिस", "वॉरेन हेस्टिंग्स", "लॉर्ड डलहौज़ी", "रॉबर्ट क्लाइव"),
        },
        "bn": {
            "prompt": "১৭৯৩ সালে বাংলায় চিরস্থায়ী বন্দোবস্ত কে চালু করেছিলেন?",
            "explanation": "১৭৯৩ সালে গভর্নর-জেনারেল লর্ড কর্নওয়ালিসের আমলে চিরস্থায়ী বন্দোবস্ত চালু হয়।",
            "options": ("লর্ড কর্নওয়ালিস", "ওয়ারেন হেস্টিংস", "লর্ড ডালহৌসি", "রবার্ট ক্লাইভ"),
        },
    },
)


def _get_matching_record(model, lookup, expected, label):
    """Return a matching seed row or stop before overwriting conflicting data."""
    record, created = model.objects.get_or_create(**lookup, defaults=expected)
    if not created and any(getattr(record, field) != value for field, value in expected.items()):
        raise CommandError(f"Existing {label} {lookup!r} conflicts with demo data; nothing was overwritten.")
    return record, created


class Command(BaseCommand):
    """Load one multilingual mock-test example into a local development database."""

    help = "Create a repeatable local English/Hindi/Bengali mock-test example."

    def handle(self, *args, **options):
        """Create stable demo rows atomically and refuse production-style settings."""
        if not settings.DEBUG:
            raise CommandError("Demo mock-test data may only be loaded with DEBUG=True development settings.")

        created = {"subject": 0, "questions": 0, "options": 0, "translations": 0, "test": 0, "test_questions": 0}
        with transaction.atomic():
            subject, was_created = _get_matching_record(
                Subject, {"slug": SUBJECT["slug"]},
                {"name": SUBJECT["name"], "description": "Local mock-test demo taxonomy.", "is_active": True},
                "subject",
            )
            created["subject"] += was_created
            mock_test, was_created = _get_matching_record(
                MockTest, {"slug": TEST["slug"]}, TEST, "mock test"
            )
            created["test"] += was_created

            for language_code, values in TEST_TRANSLATIONS.items():
                _get_matching_record(
                    MockTestTranslation,
                    {"mock_test": mock_test, "language_code": language_code},
                    {**values, "is_published": True},
                    f"{language_code} test translation",
                )

            for position, data in enumerate(QUESTIONS, start=1):
                question, was_created = _get_matching_record(
                    Question,
                    {"subject": subject, "prompt": data["prompt"]},
                    {"explanation": data["explanation"], "language": "en", "is_published": True},
                    f"question {position}",
                )
                created["questions"] += was_created

                options = []
                for option_position, text in enumerate(data["options"], start=1):
                    option, was_created = _get_matching_record(
                        QuestionOption,
                        {"question": question, "position": option_position},
                        {"text": text, "is_correct": option_position - 1 == data["correct"]},
                        f"question {position} option {option_position}",
                    )
                    options.append(option)
                    created["options"] += was_created

                for language_code in ("hi", "bn"):
                    localized = data[language_code]
                    question_translation, was_created = _get_matching_record(
                        QuestionTranslation,
                        {"question": question, "language_code": language_code},
                        {
                            "prompt": localized["prompt"],
                            "explanation": localized["explanation"],
                            "is_published": True,
                        },
                        f"question {position} {language_code} translation",
                    )
                    created["translations"] += was_created
                    for option, text in zip(options, localized["options"]):
                        _get_matching_record(
                            QuestionOptionTranslation,
                            {"question_translation": question_translation, "option": option},
                            {"text": text},
                            f"question {position} {language_code} option translation",
                        )

                join, was_created = _get_matching_record(
                    MockTestQuestion,
                    {"mock_test": mock_test, "position": position},
                    {
                        "question": question,
                        "marks": Decimal("1.00"),
                        "negative_marks": Decimal("0.25"),
                    },
                    f"test question {position}",
                )
                # A position match with a different logical question is a conflict,
                # even if the other scoring fields happen to match.
                if join.question_id != question.pk:
                    raise CommandError(f"Existing test question at position {position} conflicts; nothing was overwritten.")
                created["test_questions"] += was_created

        self.stdout.write(self.style.SUCCESS(
            "Demo mock test ready: /mock-tests/demo-wbpsc-multilingual-practice/ "
            "(5 questions; English, Hindi and Bengali). "
            f"Created rows: {created}."
        ))
