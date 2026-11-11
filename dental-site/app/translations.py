"""Bilingual English and Khmer translation layer for the Dental Clinic website."""

from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "html_lang": "en",
        "lang_label_en": "EN",
        "lang_label_km": "ខ្មែរ",
        "skip_to_content": "Skip to main content",
        "primary_nav_label": "Main navigation",
        "mobile_actions_label": "Quick clinic actions",
        "menu_open": "Open menu",
        "menu_close": "Close menu",

        # Top-level Navigation (max 6 items + persistent Book Appointment CTA)
        "nav_home": "Home",
        "nav_services": "Services",
        "nav_dentists": "Our Dentists",
        "nav_stories": "Patient Stories",
        "nav_about": "About",
        "nav_faq": "FAQ",
        "nav_book_cta": "Book Appointment",
        "nav_contact": "Contact & Book",
        "nav_privacy": "Privacy Policy",

        # Quick Actions / Mobile Bar
        "action_call": "Call",
        "action_call_us": "Call us",
        "action_message": "Message",
        "action_book": "Book",
        "action_directions": "Get Directions",

        # Clinic Status & Emergency
        "status_open_now": "Open now",
        "status_closed_now": "Currently closed",
        "hours_label": "Opening Hours",
        "address_label": "Clinic Address",
        "phone_label": "Phone",
        "timezone_note": "Times shown in Cambodia time (UTC+07:00)",
        "emergency_notice": "For dental emergencies, call [EMERGENCY PHONE: +855 XX XXX XXX].",
        "placeholder_notice": "Clinic Placeholder Preview — Replace all bracketed details with verified clinic information before launch.",

        # Foundation Home Hero & Sections
        "hero_badge": "General & Family Dental Care",
        "hero_title": "Calm, modern dental care in Phnom Penh at [CLINIC BRAND NAME]",
        "hero_subtitle": "Clear diagnosis, transparent treatment explanations, and easy online appointment requests for routine checkups and dental care.",
        "hero_cta_book": "Book Appointment",
        "hero_cta_call": "Call us",
        "section_services_title": "Dental Services",
        "section_services_subtitle": "Explore our core treatments. Exact treatment plans and quotes are confirmed after an in-clinic examination.",
        "view_all_services": "View all services",
        "view_service_details": "View details",
        "why_choose_title": "Why Patients Visit [CLINIC BRAND NAME]",
        "why_point_1_title": "Clear Treatment Explanations",
        "why_point_1_desc": "We explain findings, options, timelines, and estimated fees before any treatment begins.",
        "why_point_2_title": "Documented Sterilization Standards",
        "why_point_2_desc": "Instruments follow structured cleaning, pouching, and autoclave sterilization protocols.",
        "why_point_3_title": "Accessible Bilingual Care",
        "why_point_3_desc": "Consultations and written aftercare support are available in English and Khmer.",
        "hours_location_title": "Visit Our Clinic",
        "final_cta_title": "Ready to schedule your visit?",
        "final_cta_desc": "Send an appointment request in under a minute. Our reception team will confirm your time by phone or message.",

        # Footer
        "footer_hours_mon_fri": "Mon – Fri: 08:00 – 18:00",
        "footer_hours_sat": "Saturday: 08:00 – 17:00",
        "footer_hours_sun": "Sunday: Closed",
        "footer_social": "Connect",
        "footer_links": "Clinic Information",
        "footer_copyright": "[CLINIC LEGAL NAME]. All rights reserved.",

        # Errors & 404
        "error_404_title": "Page not found",
        "error_404_desc": "The page you requested could not be found. It may have moved or the web address may have a typo.",
        "error_404_home": "Return to Home",
        "error_500_title": "Something went wrong",
        "error_500_desc": "We could not complete your request right now. Please try again or call our clinic directly.",
    },
    "kh": {
        "html_lang": "km",
        "lang_label_en": "EN",
        "lang_label_km": "ខ្មែរ",
        "skip_to_content": "រំលងទៅខ្លឹមសារចម្បង",
        "primary_nav_label": "ម៉ឺនុយចម្បង",
        "mobile_actions_label": "សកម្មភាពរហ័សសម្រាប់អ្នកជំងឺ",
        "menu_open": "បើកម៉ឺនុយ",
        "menu_close": "បិទម៉ឺនុយ",

        # Top-level Navigation (max 6 items + persistent Book Appointment CTA)
        "nav_home": "ទំព័រដើម",
        "nav_services": "សេវាកម្ម",
        "nav_dentists": "ទន្តបណ្ឌិត",
        "nav_stories": "បទពិសោធន៍អ្នកជំងឺ",
        "nav_about": "អំពីគ្លីនិក",
        "nav_faq": "សំណួរញឹកញាប់",
        "nav_book_cta": "ណាត់ជួបពេទ្យ",
        "nav_contact": "ទំនាក់ទំនង និងណាត់ជួប",
        "nav_privacy": "គោលការណ៍ឯកជនភាព",

        # Quick Actions / Mobile Bar
        "action_call": "ហៅទូរស័ព្ទ",
        "action_call_us": "ហៅមកយើង",
        "action_message": "ផ្ញើសារ",
        "action_book": "ណាត់ជួប",
        "action_directions": "បើកផែនទី",

        # Clinic Status & Emergency
        "status_open_now": "កំពុងបើកដំណើរការ",
        "status_closed_now": "បច្ចុប្បន្នបិទ",
        "hours_label": "ម៉ោងធ្វើការ",
        "address_label": "អាសយដ្ឋានគ្លីនិក",
        "phone_label": "លេខទូរស័ព្ទ",
        "timezone_note": "ម៉ោងបង្ហាញតាមម៉ោងនៅកម្ពុជា (UTC+07:00)",
        "emergency_notice": "សម្រាប់ករណីឈឺធ្មេញបន្ទាន់ សូមហៅទៅកាន់ [លេខទូរស័ព្ទបន្ទាន់: +855 XX XXX XXX]។",
        "placeholder_notice": "គំរូព័ត៌មានបណ្តោះអាសន្ន — សូមជំនួសព័ត៌មានក្នុងវង់ក្រចកដោយទិន្នន័យគ្លីនិកពិតប្រាកដមុនពេលប្រើប្រាស់ផ្លូវការ។",

        # Foundation Home Hero & Sections
        "hero_badge": "សេវាថែទាំសុខភាពមាត់ធ្មេញទូទៅ និងគ្រួសារ",
        "hero_title": "ការថែទាំសុខភាពមាត់ធ្មេញដោយយកចិត្តទុកដាក់នៅរាជធានីភ្នំពេញ — [ឈ្មោះគ្លីនិកធ្មេញ]",
        "hero_subtitle": "ការពិនិត្យវិនិច្ឆ័យច្បាស់លាស់ ការពន្យល់ពីជម្រើសព្យាបាលប្រកបដោយតម្លាភាព និងការស្នើសុំណាត់ជួបតាមអនឡាញបានយ៉ាងងាយស្រួល។",
        "hero_cta_book": "ណាត់ជួបពេទ្យ",
        "hero_cta_call": "ហៅមកយើង",
        "section_services_title": "សេវាកម្មព្យាបាលធ្មេញ",
        "section_services_subtitle": "ស្វែងយល់ពីសេវាកម្មចម្បងរបស់យើង។ ផែនការព្យាបាល និងតម្លៃជាក់លាក់នឹងត្រូវបញ្ជាក់បន្ទាប់ពីពិនិត្យផ្ទាល់។",
        "view_all_services": "មើលសេវាកម្មទាំងអស់",
        "view_service_details": "មើលព័ត៌មានលម្អិត",
        "why_choose_title": "ហេតុអ្វីអ្នកជំងឺជ្រើសរើស [ឈ្មោះគ្លីនិកធ្មេញ]",
        "why_point_1_title": "ការពន្យល់ច្បាស់លាស់មុនព្យាបាល",
        "why_point_1_desc": "យើងពន្យល់ពីស្ថានភាពធ្មេញ ជម្រើសព្យាបាល រយៈពេល និងតម្លៃប៉ាន់ស្មានជាមុនជានិច្ច។",
        "why_point_2_title": "ស្តង់ដារសម្លាប់មេរោគត្រឹមត្រូវ",
        "why_point_2_desc": "ឧបករណ៍ពេទ្យត្រូវបានលាងសម្អាត វេចខ្ចប់ និងសម្លាប់មេរោគតាមប្រព័ន្ធ Autoclave ត្រឹមត្រូវ។",
        "why_point_3_title": "ការប្រឹក្សាជាភាសាខ្មែរ និងអង់គ្លេស",
        "why_point_3_desc": "ក្រុមការងារអាចទំនាក់ទំនង និងផ្តល់ការណែនាំក្រោយព្យាបាលទាំងភាសាខ្មែរ និងអង់គ្លេស។",
        "hours_location_title": "មកកាន់គ្លីនិករបស់យើង",
        "final_cta_title": "ត្រៀមខ្លួនរួចរាល់សម្រាប់ការណាត់ជួបហើយឬនៅ?",
        "final_cta_desc": "ផ្ញើសំណើណាត់ជួបរបស់អ្នកក្នុងរយៈពេលមិនដល់មួយនាទី។ បុគ្គលិកទទួលភ្ញៀវនឹងទាក់ទងបញ្ជាក់ជូនវិញ។",

        # Footer
        "footer_hours_mon_fri": "ចន្ទ – សុក្រ: 08:00 – 18:00",
        "footer_hours_sat": "សៅរ៍: 08:00 – 17:00",
        "footer_hours_sun": "អាទិត្យ: បិទ",
        "footer_social": "ទំនាក់ទំនងសង្គម",
        "footer_links": "ព័ត៌មានគ្លីនិក",
        "footer_copyright": "[CLINIC LEGAL NAME]។ រក្សាសិទ្ធិគ្រប់យ៉ាង។",

        # Errors & 404
        "error_404_title": "រកមិនឃើញទំព័រនេះទេ",
        "error_404_desc": "ទំព័រដែលអ្នកកំពុងស្វែងរកមិនមាន ឬត្រូវបានផ្លាស់ប្តូរទីតាំង។",
        "error_404_home": "ត្រឡប់ទៅទំព័រដើម",
        "error_500_title": "មានបញ្ហាបច្ចេកទេសបណ្តោះអាសន្ន",
        "error_500_desc": "សូមអភ័យទោស យើងមិនអាចដំណើរការសំណើរបស់អ្នកនៅពេលនេះបានទេ។ សូមព្យាយាមម្តងទៀត ឬទូរស័ព្ទមកគ្លីនិកផ្ទាល់។",
    },
}


def find_missing_translation_keys() -> dict:
    """Audit translation parity between English and Khmer dictionaries."""
    en_keys = set(TRANSLATIONS["en"].keys())
    kh_keys = set(TRANSLATIONS["kh"].keys())
    return {
        "missing_in_kh": sorted(en_keys - kh_keys),
        "missing_in_en": sorted(kh_keys - en_keys),
    }
