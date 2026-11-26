"""Leak-free multilingual NLP intent dataset for NityaMed (EN, KN, HI, Romanized, Code-Switched).

Every utterance belongs to a template `family_id` so train/test splitting via
StratifiedGroupKFold never leaks paraphrases or typo/ASR variants across splits.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UtteranceSample:
    """Single labeled utterance with language tag and leak-prevention family_id."""

    text: str
    intent: str
    lang_group: str  # en | kn | kn_rom | hi | hi_rom | code_switch
    family_id: str


def build_multilingual_dataset() -> list[UtteranceSample]:
    """Return curated multilingual utterances across 9 intents with grouped families."""
    families: list[tuple[str, str, str, list[str]]] = [
        # ================= 1. check_stock =================
        ("stk_en_1", "check_stock", "en", [
            "how many tablets do i have left",
            "how many pills are remaining in stock",
            "how mny tablts hv i left",
        ]),
        ("stk_en_2", "check_stock", "en", [
            "check my medicine inventory balance",
            "what is my current stock count",
            "check my medicin inventry",
        ]),
        ("stk_en_3", "check_stock", "en", [
            "how much medicine is remaining at home",
            "show available tablet balance in stock",
        ]),
        ("stk_en_4", "check_stock", "en", [
            "tell me remaining capsules in my bottle",
            "how many doses left in stock right now",
        ]),
        ("stk_kn_1", "check_stock", "kn", [
            "ನನ್ನ ಹತ್ತಿರ ಎಷ್ಟು ಮಾತ್ರೆಗಳು ಉಳಿದಿವೆ",
            "ಎಷ್ಟು ಮಾತ್ರೆ ಬಾಕಿ ಉಳಿದಿವೆ",
        ]),
        ("stk_kn_2", "check_stock", "kn", [
            "ನನ್ನ ಮೆಡಿಸಿನ್ ಸ್ಟಾಕ್ ಎಷ್ಟು ಇದೆ",
            "ಮೆಡಿಸಿನ್ ಸ್ಟಾಕ್ ಬ್ಯಾಲೆನ್ಸ್ ತೋರಿಸಿ",
        ]),
        ("stk_kn_3", "check_stock", "kn", [
            "ಇನ್ನು ಎಷ್ಟು ಟ್ಯಾಬ್ಲೆಟ್ ಉಳಿದಿದೆ ಹೇಳಿ",
            "ಬಾಕಿ ಇರುವ ಟ್ಯಾಬ್ಲೆಟ್ ಸಂಖ್ಯೆ ಎಷ್ಟು",
        ]),
        ("stk_kn_4", "check_stock", "kn", [
            "ನನ್ನ ಬಾಟಲಿಯಲ್ಲಿ ಎಷ್ಟು ಸ್ಟಾಕ್ ಉಳಿದಿದೆ",
            "ಉಳಿದಿರುವ ಔಷಧಿ ಸ್ಟಾಕ್ ಚೆಕ್ ಮಾಡಿ",
        ]),
        ("stk_kn_kund", "check_stock", "kn", [
            "ನನ್ ಹತ್ರ ಎಷ್ಟ್ ಗುಳಿಗೆ ಉಂಟು",
            "ಇನ್ನೂ ಎಷ್ಟ್ ಗುಳಿಗೆ ಬಾಕಿ ಉಂಟು",
        ]),
        ("stk_kn_nk", "check_stock", "kn", [
            "ನನ್ನ ಕಡೆ ಎಷ್ಟ್ ಗುಳಿಗೆ ಐತಿ",
            "ಬಾಕಿ ಗುಳಿಗೆ ಎಷ್ಟ್ ಐತಿ ಹೇಳ್ರಿ",
        ]),
        ("stk_knr_1", "check_stock", "kn_rom", [
            "nanna hatra eshtu tablet ulidide",
            "eshtu tablet ulidide check maadi",
        ]),
        ("stk_knr_2", "check_stock", "kn_rom", [
            "nanna medicine stock eshtu ide heli",
            "stock balance eshtu ide torisi",
        ]),
        ("stk_knr_3", "check_stock", "kn_rom", [
            "baki iro matre eshtu ulidide",
            "eshtu matre baki ide maneli",
        ]),
        ("stk_knr_4", "check_stock", "kn_rom", [
            "innu eshtu goli balance ide",
            "goli stock eshtu ulidide nodi",
        ]),
        ("stk_knr_reg", "check_stock", "kn_rom", [
            "nan hatra esht gulige untu",
            "esht gulige baki aiti heli",
        ]),
        ("stk_hi_1", "check_stock", "hi", [
            "मेरे पास कितनी गोलियां बची हैं",
            "मेरी कितनी गोलियां बाकी हैं",
        ]),
        ("stk_hi_2", "check_stock", "hi", [
            "मेरी दवाई का स्टॉक कितना बाकी है",
            "दवाई का स्टॉक बैलेंस बताओ",
        ]),
        ("stk_hi_3", "check_stock", "hi", [
            "कितनी टैबलेट अभी बची हुई हैं",
            "बची हुई टैबलेट की संख्या दिखाओ",
        ]),
        ("stk_hi_4", "check_stock", "hi", [
            "मेरा मेडिसिन स्टॉक चेक करो",
            "दवा की बची हुई मात्रा कितनी है",
        ]),
        ("stk_hir_1", "check_stock", "hi_rom", [
            "mere paas kitni goliyan bachi hain",
            "kitni goliyan bachi h abhi",
        ]),
        ("stk_hir_2", "check_stock", "hi_rom", [
            "meri dawai ka stock kitna bacha hai",
            "stock balance kitna remaining hai batao",
        ]),
        ("stk_hir_3", "check_stock", "hi_rom", [
            "kitni tablet baki hai check karo",
            "baki tablet count dikhao",
        ]),
        ("stk_hir_4", "check_stock", "hi_rom", [
            "dawa ka bacha hua stock bataiye",
            "bottle mein kitna stock bacha hai",
        ]),
        ("stk_hir_reg", "check_stock", "hi_rom", [
            "hamare paas kitna goli bacha ba",
            "kitni goli aur bachi hai ghar pe",
        ]),
        ("stk_cs_1", "check_stock", "code_switch", [
            "nanna medicine stock eshtu left ide",
            "how many tablets baki ide check maadi",
        ]),
        ("stk_cs_2", "check_stock", "code_switch", [
            "meri tablet ka remaining stock kitna bacha hai",
            "remaining stock check maadi please",
        ]),

        # ================= 2. today_schedule =================
        ("tod_en_1", "today_schedule", "en", [
            "which medicines should i take today",
            "what pills do i need to take today",
            "wich medicins shud i take tday",
        ]),
        ("tod_en_2", "today_schedule", "en", [
            "show my medicine schedule for today",
            "display my daily medication schedule",
            "show my medicin skedule",
        ]),
        ("tod_en_3", "today_schedule", "en", [
            "list today scheduled tablets and syrups",
            "give me today daily medicine timetable",
        ]),
        ("tod_en_4", "today_schedule", "en", [
            "what is on my medicine plan for today",
            "show all medicines due today",
        ]),
        ("tod_kn_1", "today_schedule", "kn", [
            "ಇಂದು ನಾನು ಯಾವ ಮಾತ್ರೆಗಳನ್ನು ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
            "ಇಂದು ಯಾವ ಮಾತ್ರೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
        ]),
        ("tod_kn_2", "today_schedule", "kn", [
            "ಇವತ್ತಿನ ಮೆಡಿಸಿನ್ ಶೆಡ್ಯೂಲ್ ತೋರಿಸಿ",
            "ದಿನದ ಮೆಡಿಸಿನ್ ಶೆಡ್ಯೂಲ್ ಕೊಡಿ",
        ]),
        ("tod_kn_3", "today_schedule", "kn", [
            "ಇವತ್ತು ತೆಗೆದುಕೊಳ್ಳಬೇಕಾದ ಔಷಧಿ ಪಟ್ಟಿ ತೋರಿಸಿ",
            "ಇಂದಿನ ಔಷಧಿಗಳ ಪಟ್ಟಿ ಏನು",
        ]),
        ("tod_kn_4", "today_schedule", "kn", [
            "ಇವತ್ತು ಬೆಳಗ್ಗೆ ರಾತ್ರಿ ಯಾವ ಟ್ಯಾಬ್ಲೆಟ್ ಇದೆ",
            "ಇಂದು ಯಾವ ಟ್ಯಾಬ್ಲೆಟ್ ಶೆಡ್ಯೂಲ್ ಆಗಿದೆ",
        ]),
        ("tod_kn_reg", "today_schedule", "kn", [
            "ಇವತ್ತ್ ಯಾವ್ ಗುಳಿಗೆ ತಿನ್ಬೇಕು",
            "ಇವತ್ತಿಗೆ ಯಾವ ಗುಳಿಗೆ ಉಂಟು ಹೇಳಿ",
        ]),
        ("tod_knr_1", "today_schedule", "kn_rom", [
            "ivattu naanu yava tablet togobeku",
            "ivattu yava tablet ide heli",
        ]),
        ("tod_knr_2", "today_schedule", "kn_rom", [
            "ivattina medicine schedule torisi",
            "daily medicine schedule torisu",
        ]),
        ("tod_knr_3", "today_schedule", "kn_rom", [
            "today yava matre tagobeku heli",
            "ivattu yava matre list ide",
        ]),
        ("tod_knr_4", "today_schedule", "kn_rom", [
            "ivattu beligge ratri yava goli togobeku",
            "today timetable torisi medicine du",
        ]),
        ("tod_knr_reg", "today_schedule", "kn_rom", [
            "ivatt yav gulige untu helri",
            "ivattina gulige list torisri",
        ]),
        ("tod_hi_1", "today_schedule", "hi", [
            "आज मुझे कौन सी दवाइयां लेनी हैं",
            "आज कौन सी दवाई लेनी है",
        ]),
        ("tod_hi_2", "today_schedule", "hi", [
            "आज का दवा का शेड्यूल दिखाओ",
            "मेरा आज का मेडिसिन शेड्यूल बताओ",
        ]),
        ("tod_hi_3", "today_schedule", "hi", [
            "आज कौन सी गोली खानी है बताओ",
            "आज की गोलियों की लिस्ट दिखाओ",
        ]),
        ("tod_hi_4", "today_schedule", "hi", [
            "आज सुबह और शाम की दवाई की लिस्ट दिखाएं",
            "दैनिक दवा शेड्यूल बताइए",
        ]),
        ("tod_hir_1", "today_schedule", "hi_rom", [
            "aaj mujhe kaunsi dawai leni hai",
            "aaj kaun si dawai leni h",
        ]),
        ("tod_hir_2", "today_schedule", "hi_rom", [
            "aaj ka medicine schedule dikhao",
            "mera daily schedule batao",
        ]),
        ("tod_hir_3", "today_schedule", "hi_rom", [
            "aaj kaunsi goli khani hai batao",
            "aaj ki goli list dikhaiye",
        ]),
        ("tod_hir_4", "today_schedule", "hi_rom", [
            "aaj subah sham konsi tablet leni hai",
            "today dawai timetable batao",
        ]),
        ("tod_cs_1", "today_schedule", "code_switch", [
            "ivattu schedule yavdu ide show maadi",
            "today yava medicine togobeku tell me",
        ]),
        ("tod_cs_2", "today_schedule", "code_switch", [
            "aaj ki medicines schedule dikhao please",
            "today ka medicine timetable list karo",
        ]),

        # ================= 3. next_dose =================
        ("nxt_en_1", "next_dose", "en", [
            "when is my next dose",
            "wen is my nxt dose",
        ]),
        ("nxt_en_2", "next_dose", "en", [
            "what time is my upcoming medicine due",
            "when do i take my next pill",
        ]),
        ("nxt_en_3", "next_dose", "en", [
            "tell me my next reminder time",
            "when is the next scheduled tablet",
        ]),
        ("nxt_en_4", "next_dose", "en", [
            "which medicine is due next and at what time",
            "how soon is my next dose",
        ]),
        ("nxt_kn_1", "next_dose", "kn", [
            "ನನ್ನ ಮುಂದಿನ ಡೋಸ್ ಯಾವಾಗ ಇದೆ",
            "ಮುಂದಿನ ಡೋಸ್ ಸಮಯ ಯಾವಾಗ",
        ]),
        ("nxt_kn_2", "next_dose", "kn", [
            "ಮುಂದಿನ ಮಾತ್ರೆ ಎಷ್ಟು ಗಂಟೆಗೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
            "ಮುಂದಿನ ಮಾತ್ರೆ ಯಾವಾಗ",
        ]),
        ("nxt_kn_3", "next_dose", "kn", [
            "ನೆಕ್ಸ್ಟ್ ಟ್ಯಾಬ್ಲೆಟ್ ಟೈಮ್ ಹೇಳಿ",
            "ಮುಂದಿನ ಔಷಧಿ ಟೈಮ್ ಎಷ್ಟು",
        ]),
        ("nxt_kn_4", "next_dose", "kn", [
            "ಮುಂದಿನ ರಿಮೈಂಡರ್ ಯಾವಾಗ ಬರುತ್ತದೆ",
            "ಮುಂದಿನ ಔಷಧಿ ಯಾವಾಗ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
        ]),
        ("nxt_knr_1", "next_dose", "kn_rom", [
            "nanna mundina dose yavaga ide",
            "mundina dose time yavaga heli",
        ]),
        ("nxt_knr_2", "next_dose", "kn_rom", [
            "next tablet eshtu gantege togobeku",
            "next dose time eshtu gantege",
        ]),
        ("nxt_knr_3", "next_dose", "kn_rom", [
            "mundina matre yavaga tagobeku",
            "mundina goli yavagide heli",
        ]),
        ("nxt_knr_4", "next_dose", "kn_rom", [
            "next medicine reminder yavaga barutte",
            "next dose yavaga ide torisi",
        ]),
        ("nxt_hi_1", "next_dose", "hi", [
            "मेरी अगली खुराक कब है",
            "अगली खुराक का समय क्या है",
        ]),
        ("nxt_hi_2", "next_dose", "hi", [
            "अगली दवाई कितने बजे लेनी है",
            "अगली दवाई कब लेनी है बताओ",
        ]),
        ("nxt_hi_3", "next_dose", "hi", [
            "नेक्स्ट डोज का टाइम कब है",
            "नेक्स्ट डोज कितने बजे है",
        ]),
        ("nxt_hi_4", "next_dose", "hi", [
            "अगली गोली कब खानी है बताओ",
            "मेरा अगला रिमाइंडर कब आएगा",
        ]),
        ("nxt_hir_1", "next_dose", "hi_rom", [
            "meri agli dose kab hai",
            "agli dose ka time kya hai",
        ]),
        ("nxt_hir_2", "next_dose", "hi_rom", [
            "next dawai kitne baje leni hai",
            "agli dawai kab leni h batao",
        ]),
        ("nxt_hir_3", "next_dose", "hi_rom", [
            "agla goli kab khana hai batao",
            "next tablet kitne baje khani hai",
        ]),
        ("nxt_hir_4", "next_dose", "hi_rom", [
            "next dose kab aayega",
            "agla reminder time bataiye",
        ]),
        ("nxt_cs_1", "next_dose", "code_switch", [
            "nanna next dose yavaga ide heli",
            "agli medicine kab take karni hai",
        ]),
        ("nxt_cs_2", "next_dose", "code_switch", [
            "next dose time yavaga aur kab hai",
            "next tablet kitne baje togobeku",
        ]),

        # ================= 4. medicine_info =================
        ("inf_en_1", "medicine_info", "en", [
            "why is this medicine used",
            "y is this medicin used",
        ]),
        ("inf_en_2", "medicine_info", "en", [
            "what is this tablet commonly used for",
            "tell me common uses and side effects of this drug",
        ]),
        ("inf_en_3", "medicine_info", "en", [
            "explain how this medicine works",
            "what is the mechanism and category of this medicine",
        ]),
        ("inf_en_4", "medicine_info", "en", [
            "what precautions and side effects should i know",
            "show verified information for this tablet",
        ]),
        ("inf_kn_1", "medicine_info", "kn", [
            "ಈ ಮಾತ್ರೆಯನ್ನು ಏಕೆ ಉಪಯೋಗಿಸುತ್ತಾರೆ",
            "ಈ ಮಾತ್ರೆಯ ಉಪಯೋಗ ಏನು",
        ]),
        ("inf_kn_2", "medicine_info", "kn", [
            "ಈ ಔಷಧಿಯ ಉಪಯೋಗ ಮತ್ತು ಅಡ್ಡಪರಿಣಾಮಗಳು ಏನು",
            "ಈ ಔಷಧಿಯ ಅಡ್ಡಪರಿಣಾಮಗಳು ಮತ್ತು ಮುನ್ನೆಚ್ಚರಿಕೆ ಏನು",
        ]),
        ("inf_kn_3", "medicine_info", "kn", [
            "ಈ ಟ್ಯಾಬ್ಲೆಟ್ ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ",
            "ಈ ಟ್ಯಾಬ್ಲೆಟ್ ಬಗ್ಗೆ ವಿವರ ತಿಳಿಸಿ",
        ]),
        ("inf_kn_4", "medicine_info", "kn", [
            "ಈ ಮೆಡಿಸಿನ್ ಬಗ್ಗೆ ಮಾಹಿತಿ ನೀಡಿ",
            "ಈ ಔಷಧಿ ಯಾವುದಕ್ಕೆ ಉಪಯೋಗಿಸುತ್ತಾರೆ",
        ]),
        ("inf_knr_1", "medicine_info", "kn_rom", [
            "ee tablet yake use maadtare",
            "ee tablet yavudakke use agutte",
        ]),
        ("inf_knr_2", "medicine_info", "kn_rom", [
            "ee medicine bagge mahiti kodi",
            "ee medicine information torisi",
        ]),
        ("inf_knr_3", "medicine_info", "kn_rom", [
            "ee matre side effects mattu uses heli",
            "ee tablet precautions mattu uses yenu",
        ]),
        ("inf_knr_4", "medicine_info", "kn_rom", [
            "idu hege kelasa madutte explain maadi",
            "ee goli yake kodtare doctor",
        ]),
        ("inf_hi_1", "medicine_info", "hi", [
            "यह दवाई किस काम आती है",
            "यह दवाई किस लिए इस्तेमाल होती है",
        ]),
        ("inf_hi_2", "medicine_info", "hi", [
            "इस गोली के उपयोग और साइड इफेक्ट क्या हैं",
            "इस दवाई की सावधानियां और साइड इफेक्ट बताओ",
        ]),
        ("inf_hi_3", "medicine_info", "hi", [
            "यह दवा कैसे काम करती है",
            "यह टैबलेट शरीर में कैसे असर करती है",
        ]),
        ("inf_hi_4", "medicine_info", "hi", [
            "इस टैबलेट के बारे में जानकारी दो",
            "इस दवाई के उपयोग बताइए",
        ]),
        ("inf_hir_1", "medicine_info", "hi_rom", [
            "ye dawai kis kaam aati hai",
            "ye dawa kyun use hoti hai",
        ]),
        ("inf_hir_2", "medicine_info", "hi_rom", [
            "is tablet ke uses aur side effects batao",
            "is goli ke side effects kya hain",
        ]),
        ("inf_hir_3", "medicine_info", "hi_rom", [
            "is medicine ka kaam kya hai samjhao",
            "ye dawai kaise kaam karti hai",
        ]),
        ("inf_hir_4", "medicine_info", "hi_rom", [
            "is dawa ki precautions aur information dikhao",
            "is tablet ke bare mein jankari do",
        ]),
        ("inf_cs_1", "medicine_info", "code_switch", [
            "ee medicine ka common use kya hai heli",
            "is tablet ke side effects yenu ide",
        ]),
        ("inf_cs_2", "medicine_info", "code_switch", [
            "ee tablet uses mattu precautions explain maadi",
            "ye medicine ke precautions yenu irutte",
        ]),

        # ================= 5. adherence_status =================
        ("adh_en_1", "adherence_status", "en", [
            "have i taken my morning medicine",
            "hav i takn my mrning medicin",
        ]),
        ("adh_en_2", "adherence_status", "en", [
            "did i already take my evening pill",
            "did i skip or take my afternoon dose",
        ]),
        ("adh_en_3", "adherence_status", "en", [
            "check if i confirmed my morning dose",
            "which doses did i complete today",
        ]),
        ("adh_en_4", "adherence_status", "en", [
            "show my adherence report and dose history",
            "did i miss any scheduled tablet earlier",
        ]),
        ("adh_kn_1", "adherence_status", "kn", [
            "ನಾನು ಬೆಳಗಿನ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡಿದ್ದೇನಾ",
            "ಬೆಳಗ್ಗೆ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆನಾ",
        ]),
        ("adh_kn_2", "adherence_status", "kn", [
            "ಇಂದು ಎಷ್ಟು ಡೋಸ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ತೋರಿಸಿ",
            "ಇಂದಿನ ಡೋಸ್ ಹಿಸ್ಟರಿ ತೋರಿಸಿ",
        ]),
        ("adh_kn_3", "adherence_status", "kn", [
            "ಸಂಜೆಯ ಟ್ಯಾಬ್ಲೆಟ್ ತೆಗೆದುಕೊಂಡೆನಾ ನೋಡಿ",
            "ಮಧ್ಯಾಹ್ನದ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡಿದ್ದೇನಾ ಚೆಕ್ ಮಾಡಿ",
        ]),
        ("adh_kn_4", "adherence_status", "kn", [
            "ನನ್ನ ಅಡ್ಹಿಯರೆನ್ಸ್ ಸ್ಟೇಟಸ್ ಚೆಕ್ ಮಾಡಿ",
            "ಯಾವ ಡೋಸ್ ಬಾಕಿ ಅಥವಾ ಸ್ಕಿಪ್ ಆಗಿದೆ",
        ]),
        ("adh_knr_1", "adherence_status", "kn_rom", [
            "naanu beligge tablet togondidna",
            "morning medicine togondidena check maadi",
        ]),
        ("adh_knr_2", "adherence_status", "kn_rom", [
            "ivattu eshtu dose complete agide",
            "nanna today dose status torisi",
        ]),
        ("adh_knr_3", "adherence_status", "kn_rom", [
            "evening goli togondna illa skip agidya",
            "sanje tablet togondena nodi",
        ]),
        ("adh_knr_4", "adherence_status", "kn_rom", [
            "adherence report mattu history torisi",
            "naanu ivattu dose miss madidna",
        ]),
        ("adh_hi_1", "adherence_status", "hi", [
            "क्या मैंने सुबह की दवाई ले ली है",
            "सुबह की गोली मैंने खाई क्या",
        ]),
        ("adh_hi_2", "adherence_status", "hi", [
            "मैंने आज की गोली खाई या नहीं",
            "आज मैंने कौन सी दवा खाई है",
        ]),
        ("adh_hi_3", "adherence_status", "hi", [
            "मेरा आज का डोज स्टेटस चेक करो",
            "आज का अड्हीरेंस स्टेटस दिखाओ",
        ]),
        ("adh_hi_4", "adherence_status", "hi", [
            "शाम की टैबलेट ली क्या मैंने",
            "क्या कोई डोज छूटी है आज",
        ]),
        ("adh_hir_1", "adherence_status", "hi_rom", [
            "kya maine subah ki dawai le li hai",
            "morning tablet liya kya maine check karo",
        ]),
        ("adh_hir_2", "adherence_status", "hi_rom", [
            "aaj ka dose status batao",
            "today kitne dose confirm hue",
        ]),
        ("adh_hir_3", "adherence_status", "hi_rom", [
            "sham ki goli khayi ya skip ki",
            "maine raat ki dawai li thi kya",
        ]),
        ("adh_hir_4", "adherence_status", "hi_rom", [
            "adherence history dikhao meri",
            "kya maine aaj koi dose miss kiya",
        ]),
        ("adh_cs_1", "adherence_status", "code_switch", [
            "morning dose togondidna check karo",
            "did i take subah ki dawai today",
        ]),
        ("adh_cs_2", "adherence_status", "code_switch", [
            "today dose status torisi please",
            "morning tablet khaya kya check maadi",
        ]),

        # ================= 6. refill_check =================
        ("ref_en_1", "refill_check", "en", [
            "when should i refill my medicine",
            "wen shud i refil my medicin",
        ]),
        ("ref_en_2", "refill_check", "en", [
            "when will my tablets run out",
            "when is the depletion date for my stock",
        ]),
        ("ref_en_3", "refill_check", "en", [
            "how many days of supply do i have left",
            "how long will my current stock last",
        ]),
        ("ref_en_4", "refill_check", "en", [
            "show my upcoming refill alerts",
            "which medicine needs refilling soon",
        ]),
        ("ref_kn_1", "refill_check", "kn", [
            "ನಾನು ಯಾವಾಗ ಹೊಸ ಮಾತ್ರೆ ಖರೀದಿಸಬೇಕು",
            "ಯಾವಾಗ ರಿಫಿಲ್ ಮಾಡಿಸಬೇಕು",
        ]),
        ("ref_kn_2", "refill_check", "kn", [
            "ನನ್ನ ಔಷಧಿ ಸ್ಟಾಕ್ ಯಾವಾಗ ಖಾಲಿಯಾಗುತ್ತದೆ",
            "ಟ್ಯಾಬ್ಲೆಟ್ ಯಾವಾಗ ಮುಗಿಯುತ್ತದೆ",
        ]),
        ("ref_kn_3", "refill_check", "kn", [
            "ರಿಫಿಲ್ ಅಲರ್ಟ್ ದಿನಾಂಕ ಯಾವಾಗ ಇದೆ",
            "ರಿಫಿಲ್ ದಿನಾಂಕ ತೋರಿಸಿ",
        ]),
        ("ref_kn_4", "refill_check", "kn", [
            "ಇನ್ನು ಎಷ್ಟು ದಿನಕ್ಕೆ ಮಾತ್ರೆ ಸಾಕಾಗುತ್ತದೆ",
            "ಸ್ಟಾಕ್ ಎಷ್ಟು ದಿನ ಬರುತ್ತದೆ ಹೇಳಿ",
        ]),
        ("ref_kn_reg", "refill_check", "kn", [
            "ಗುಳಿಗೆ ಯಾವಾಗ್ ಮುಗೀತು ಹೇಳಿ",
            "ಇನ್ ಎಷ್ಟ್ ದಿನಕ್ ಗುಳಿಗೆ ಖಾಲಿ ಆಗ್ತದೆ",
        ]),
        ("ref_knr_1", "refill_check", "kn_rom", [
            "naanu yavaga medicine refill madbeku",
            "refill yavaga madbeku heli",
        ]),
        ("ref_knr_2", "refill_check", "kn_rom", [
            "nanna tablets yavaga khali agutte",
            "yava tablet bega mugiyutte",
        ]),
        ("ref_knr_3", "refill_check", "kn_rom", [
            "innu eshtu dina barutte ee stock",
            "eshtu dina stock sakagutte",
        ]),
        ("ref_knr_4", "refill_check", "kn_rom", [
            "refill alert date yavaga ide torisi",
            "new strip yavaga tagobeku",
        ]),
        ("ref_hi_1", "refill_check", "hi", [
            "मुझे अपनी दवाई कब रीफिल करनी चाहिए",
            "दवाई कब रीफिल करनी है",
        ]),
        ("ref_hi_2", "refill_check", "hi", [
            "मेरी गोलियां कब खत्म होंगी",
            "स्टॉक किस तारीख को खत्म होगा",
        ]),
        ("ref_hi_3", "refill_check", "hi", [
            "यह स्टॉक कितने दिन और चलेगा",
            "दवाई कितने दिन चलेगी बताओ",
        ]),
        ("ref_hi_4", "refill_check", "hi", [
            "रीफिल अलर्ट की तारीख बताओ",
            "नई स्ट्रिप कब खरीदनी पड़ेगी",
        ]),
        ("ref_hir_1", "refill_check", "hi_rom", [
            "mujhe dawai kab refill karni chahiye",
            "refill kab karna padega batao",
        ]),
        ("ref_hir_2", "refill_check", "hi_rom", [
            "meri tablet kab khatam hogi",
            "dawai kab khatam hone wali hai",
        ]),
        ("ref_hir_3", "refill_check", "hi_rom", [
            "ye stock kitne din chalega",
            "kitne din ki dawai aur bachi hai",
        ]),
        ("ref_hir_4", "refill_check", "hi_rom", [
            "nayi strip kab kharidni padegi",
            "refill alert date bataiye",
        ]),
        ("ref_cs_1", "refill_check", "code_switch", [
            "nanna stock yavaga khatam hoga refill check maadi",
            "how many days chalega ye tablet",
        ]),
        ("ref_cs_2", "refill_check", "code_switch", [
            "refill date yavaga aur kab kharidni hai",
            "stock eshtu days chalega batao",
        ]),

        # ================= 7. confirm_dose =================
        ("cnf_en_1", "confirm_dose", "en", [
            "i just took my morning tablet",
            "i took my mrng tablt",
        ]),
        ("cnf_en_2", "confirm_dose", "en", [
            "mark my current dose as taken",
            "confirm that i took my pill now",
        ]),
        ("cnf_en_3", "confirm_dose", "en", [
            "record my evening medicine intake",
            "log my afternoon dose as taken",
        ]),
        ("cnf_en_4", "confirm_dose", "en", [
            "i swallowed my scheduled capsule",
            "save my dose confirmation as taken",
        ]),
        ("cnf_kn_1", "confirm_dose", "kn", [
            "ನಾನು ಈಗಷ್ಟೇ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆ",
            "ನಾನು ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆ",
        ]),
        ("cnf_kn_2", "confirm_dose", "kn", [
            "ಬೆಳಗಿನ ಡೋಸ್ ತೆಗೆದುಕೊಂಡೆ ಎಂದು ಗುರುತಿಸಿ",
            "ಡೋಸ್ ತೆಗೆದುಕೊಂಡೆ ಎಂದು ಮಾರ್ಕ್ ಮಾಡಿ",
        ]),
        ("cnf_kn_3", "confirm_dose", "kn", [
            "ಸಂಜೆಯ ಟ್ಯಾಬ್ಲೆಟ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ಕನ್ಫರ್ಮ್ ಮಾಡಿ",
            "ರಾತ್ರಿ ಟ್ಯಾಬ್ಲೆಟ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ಅಪ್ಡೇಟ್ ಮಾಡಿ",
        ]),
        ("cnf_kn_4", "confirm_dose", "kn", [
            "ನನ್ನ ಇಂದಿನ ಔಷಧಿ ತೆಗೆದುಕೊಂಡೆ ಸೇವ್ ಮಾಡಿ",
            "ಟ್ಯಾಬ್ಲೆಟ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ದಾಖಲಿಸಿ",
        ]),
        ("cnf_kn_reg", "confirm_dose", "kn", [
            "ನಾನ್ ಇವಾಗ್ ಗುಳಿಗೆ ತಿಂದೆ",
            "ಬೆಳ್ಗಿನ ಗುಳಿಗೆ ನುಂಗಿದೆ ಮಾರ್ಕ್ ಮಾಡ್ರಿ",
        ]),
        ("cnf_knr_1", "confirm_dose", "kn_rom", [
            "naanu eega tablet togonde",
            "tablet togonde antha mark maadi",
        ]),
        ("cnf_knr_2", "confirm_dose", "kn_rom", [
            "morning matre togonde confirm maadi",
            "dose taken antha confirm maadi",
        ]),
        ("cnf_knr_3", "confirm_dose", "kn_rom", [
            "night goli togonde update maadu",
            "evening tablet togondiddini save maadi",
        ]),
        ("cnf_knr_4", "confirm_dose", "kn_rom", [
            "beligge medicine togonde log maadi",
            "dose complete madide confirm maadi",
        ]),
        ("cnf_hi_1", "confirm_dose", "hi", [
            "मैंने अपनी सुबह की गोली ले ली है",
            "मैंने अभी गोली खा ली है",
        ]),
        ("cnf_hi_2", "confirm_dose", "hi", [
            "मेरा डोज टेकन मार्क कर दो",
            "डोज को टेकन मार्क करो",
        ]),
        ("cnf_hi_3", "confirm_dose", "hi", [
            "अभी मैंने दवाई ले ली है कन्फर्म करो",
            "दवाई खा ली है सेव कर दो",
        ]),
        ("cnf_hi_4", "confirm_dose", "hi", [
            "रात की टैबलेट खा ली है अपडेट करो",
            "शाम की डोज कन्फर्म कर दीजिए",
        ]),
        ("cnf_hir_1", "confirm_dose", "hi_rom", [
            "maine abhi goli kha li hai",
            "goli kha li hai maine",
        ]),
        ("cnf_hir_2", "confirm_dose", "hi_rom", [
            "morning dawai le li mark kar do",
            "dose taken mark karo",
        ]),
        ("cnf_hir_3", "confirm_dose", "hi_rom", [
            "mera dose confirm kar do taken",
            "maine tablet le li confirm karo",
        ]),
        ("cnf_hir_4", "confirm_dose", "hi_rom", [
            "raat ki tablet le li hai update karo",
            "dawai pi liya maine log karo",
        ]),
        ("cnf_cs_1", "confirm_dose", "code_switch", [
            "morning tablet togonde please confirm maadi",
            "maine dose le liya mark taken karo",
        ]),
        ("cnf_cs_2", "confirm_dose", "code_switch", [
            "i took evening goli confirm maadi",
            "tablet togonde mark taken kar do",
        ]),

        # ================= 8. update_stock_purchase =================
        ("pur_en_1", "update_stock_purchase", "en", [
            "i purchased another strip update my stock",
            "i purchsed one more strip updat stok",
        ]),
        ("pur_en_2", "update_stock_purchase", "en", [
            "add one new strip to my medicine inventory",
            "i bought two strips today please add stock",
        ]),
        ("pur_en_3", "update_stock_purchase", "en", [
            "add ten tablets to my stock balance",
            "restock my medicine with fifteen units",
        ]),
        ("pur_en_4", "update_stock_purchase", "en", [
            "record a new bottle purchase in inventory",
            "update stock i bought a fresh pack",
        ]),
        ("pur_kn_1", "update_stock_purchase", "kn", [
            "ನಾನು ಹೊಸ ಸ್ಟ್ರಿಪ್ ಖರೀದಿಸಿದ್ದೇನೆ ಸ್ಟಾಕ್ ಅಪ್ಡೇಟ್ ಮಾಡಿ",
            "ಹೊಸ ಸ್ಟ್ರಿಪ್ ಖರೀದಿಸಿದ್ದೇನೆ ಸೇರಿಸಿ",
        ]),
        ("pur_kn_2", "update_stock_purchase", "kn", [
            "ಹತ್ತು ಮಾತ್ರೆಗಳನ್ನು ಸ್ಟಾಕ್‌ಗೆ ಸೇರಿಸಿ",
            "ಇಪ್ಪತ್ತು ಟ್ಯಾಬ್ಲೆಟ್ ಸ್ಟಾಕ್ ಆಡ್ ಮಾಡಿ",
        ]),
        ("pur_kn_3", "update_stock_purchase", "kn", [
            "ಎರಡು ಸ್ಟ್ರಿಪ್ ತಂದಿದ್ದೇನೆ ಇನ್ವೆಂಟರಿ ಅಪ್ಡೇಟ್ ಮಾಡಿ",
            "ಒಂದು ಬಾಟಲ್ ಸಿರಪ್ ತಂದಿದ್ದೇನೆ ಸ್ಟಾಕ್ ಹೆಚ್ಚಿಸಿ",
        ]),
        ("pur_kn_4", "update_stock_purchase", "kn", [
            "ಮೆಡಿಸಿನ್ ಪರ್ಚೇಸ್ ಎಂಟ್ರಿ ಮಾಡಿ",
            "ಹೊಸ ಪ್ಯಾಕ್ ತಂದಿದ್ದೇನೆ ಸ್ಟಾಕ್ ಅಪ್ಡೇಟ್ ಮಾಡಿ",
        ]),
        ("pur_kn_reg", "update_stock_purchase", "kn", [
            "ಹೊಸ ಗುಳಿಗೆ ಪತ್ತಾ ತಂದಿನಿ ಸ್ಟಾಕ್ ಸೇರಿಸ್ರಿ",
            "ಇನ್ನೊಂದ್ ಸ್ಟ್ರಿಪ್ ತಗೊಂಡ್ ಬಂದು ಸ್ಟಾಕ್ ಹಾಕ್ರಿ",
        ]),
        ("pur_knr_1", "update_stock_purchase", "kn_rom", [
            "naanu hosa strip tandiddene stock update maadi",
            "hosa strip purchase madide stock update maadi",
        ]),
        ("pur_knr_2", "update_stock_purchase", "kn_rom", [
            "ondu strip tagonde inventory ge add maadi",
            "eradu strip add maadi stock ge",
        ]),
        ("pur_knr_3", "update_stock_purchase", "kn_rom", [
            "hattu tablet purchase madidini add maadu",
            "hosa goli packet serisi stock ge",
        ]),
        ("pur_knr_4", "update_stock_purchase", "kn_rom", [
            "innond strip buy madide stock serisi",
            "eradu bottle tagonde inventory update maadi",
        ]),
        ("pur_hi_1", "update_stock_purchase", "hi", [
            "मैंने एक नया पत्ता खरीदा है स्टॉक अपडेट करो",
            "नया पत्ता खरीदा है स्टॉक बढ़ाओ",
        ]),
        ("pur_hi_2", "update_stock_purchase", "hi", [
            "दस गोलियां स्टॉक में जोड़ दो",
            "पंद्रह टैबलेट इन्वेंटरी में ऐड करो",
        ]),
        ("pur_hi_3", "update_stock_purchase", "hi", [
            "नई बोतल लाया हूं इन्वेंटरी बढ़ाओ",
            "दो स्ट्रिप खरीदी हैं स्टॉक अपडेट कीजिए",
        ]),
        ("pur_hi_4", "update_stock_purchase", "hi", [
            "दवाई खरीद ली है स्टॉक में डाल दो",
            "नया पैक खरीदा है स्टॉक जोड़िए",
        ]),
        ("pur_hir_1", "update_stock_purchase", "hi_rom", [
            "maine ek aur patta kharida hai stock update karo",
            "ek patta kharida hai stock mein add karo",
        ]),
        ("pur_hir_2", "update_stock_purchase", "hi_rom", [
            "ek strip laya hoon inventory mein add karo",
            "do strip kharidi hain stock badhao",
        ]),
        ("pur_hir_3", "update_stock_purchase", "hi_rom", [
            "das tablet aur buy kiya hai jodo",
            "naya dabba laya hoon add stock karo",
        ]),
        ("pur_hir_4", "update_stock_purchase", "hi_rom", [
            "naya bottle kharid liya stock update kar do",
            "medicine purchase add karo inventory mein",
        ]),
        ("pur_cs_1", "update_stock_purchase", "code_switch", [
            "ondu strip buy maadide stock update karo",
            "i purchased ek patta please add maadi",
        ]),
        ("pur_cs_2", "update_stock_purchase", "code_switch", [
            "new strip bought inventory update maadi",
            "ten tablets kharida hai stock add maadu",
        ]),

        # ================= 9. out_of_scope =================
        ("oos_clin_1", "out_of_scope", "en", [
            "should i stop taking my blood pressure tablet",
            "can i stop my heart medicine now",
        ]),
        ("oos_clin_2", "out_of_scope", "en", [
            "can i double my dose tonight because i missed one",
            "should i increase or decrease my dosage",
        ]),
        ("oos_clin_3", "out_of_scope", "en", [
            "do i have diabetes or hypertension based on my pills",
            "diagnose my chest pain and headache",
        ]),
        ("oos_clin_4", "out_of_scope", "en", [
            "which new antibiotic should i buy for fever",
            "prescribe a better painkiller for my knee",
        ]),
        ("oos_clin_5", "out_of_scope", "kn", [
            "ನಾನು ಬಿಪಿ ಮಾತ್ರೆ ನಿಲ್ಲಿಸಬಹುದಾ",
            "ಜ್ವರಕ್ಕೆ ಯಾವ ಹೊಸ ಆಂಟಿಬಯೋಟಿಕ್ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
        ]),
        ("oos_clin_6", "out_of_scope", "kn_rom", [
            "naanu bp tablet nilisabahuda heli",
            "jvara ide yava antibiotic togobeku",
        ]),
        ("oos_clin_7", "out_of_scope", "hi", [
            "क्या मैं अपनी शुगर की गोली बंद कर दूं",
            "बुखार के लिए कौन सी नई दवाई खरीदूं",
        ]),
        ("oos_clin_8", "out_of_scope", "hi_rom", [
            "kya main apni sugar ki goli band kar doon",
            "bukhar hai kaunsi nayi dawai loon",
        ]),
        ("oos_gen_1", "out_of_scope", "en", [
            "what is the weather forecast tomorrow",
            "will it rain in bengaluru today",
        ]),
        ("oos_gen_2", "out_of_scope", "en", [
            "tell me todays cricket match score",
            "who won the world cup final",
        ]),
        ("oos_gen_3", "out_of_scope", "en", [
            "book a cab to the railway station",
            "order dinner from a restaurant",
        ]),
        ("oos_gen_4", "out_of_scope", "en", [
            "play some kannada movie songs",
            "tell me a funny joke",
        ]),
        ("oos_gen_5", "out_of_scope", "kn", [
            "ಇಂದು ಮಳೆ ಬರುತ್ತದೆಯೇ ಹೇಳಿ",
            "ನಾಳೆ ಹವಾಮಾನ ಹೇಗಿರುತ್ತದೆ",
        ]),
        ("oos_gen_6", "out_of_scope", "kn", [
            "ಕ್ರಿಕೆಟ್ ಸ್ಕೋರ್ ಎಷ್ಟು ಆಗಿದೆ",
            "ಒಂದು ಹಾಡು ಪ್ಲೇ ಮಾಡಿ",
        ]),
        ("oos_gen_7", "out_of_scope", "kn_rom", [
            "ivattu male barutta weather heli",
            "cricket score eshtu agide",
        ]),
        ("oos_gen_8", "out_of_scope", "hi", [
            "कल मौसम कैसा रहेगा बताओ",
            "आज बारिश होगी क्या",
        ]),
        ("oos_gen_9", "out_of_scope", "hi", [
            "मुझे एक गाना सुनाओ",
            "क्रिकेट मैच का स्कोर बताओ",
        ]),
        ("oos_gen_10", "out_of_scope", "hi_rom", [
            "kal mausam kaisa rahega batao",
            "cricket match ka score kya hua",
        ]),

        # ================= REAL-WORLD EXPANSION: check_stock =================
        ("stk_rw_en_1", "check_stock", "en", [
            "how many dolo tablets are left",
            "dolo 650 stock balance check",
            "check remaining count of metformin",
        ]),
        ("stk_rw_en_2", "check_stock", "en", [
            "do i have enough pan d capsules left",
            "is there any paracetamol remaining in my stock",
        ]),
        ("stk_rw_en_3", "check_stock", "en", [
            "check stock of my blood pressure tablets",
            "how full is my syrup bottle",
        ]),
        ("stk_rw_kn_1", "check_stock", "kn", [
            "ಡೋಲೋ ಮಾತ್ರೆ ಇನ್ನು ಎಷ್ಟಿದೆ",
            "ಮೆಟ್ಫಾರ್ಮಿನ್ ಎಷ್ಟು ಮಾತ್ರೆ ಉಳಿದಿದೆ",
        ]),
        ("stk_rw_kn_2", "check_stock", "kn", [
            "ನನ್ನಲ್ಲಿ ಇರೋ ಸ್ಟಾಕ್ ಲೆಕ್ಕ ಹೇಳಿ",
            "ಮನೆಯಲ್ಲಿ ಎಷ್ಟು ಗುಳಿಗೆ ಬಾಕಿ ಇದೆ",
        ]),
        ("stk_rw_kn_3", "check_stock", "kn", [
            "ಪ್ಯಾನ್ ಡಿ ಕ್ಯಾಪ್ಸುಲ್ ಎಷ್ಟು ಉಳಿದಿದೆ",
            "ಕ್ರೋಸಿನ್ ಸ್ಟಾಕ್ ಬ್ಯಾಲೆನ್ಸ್ ತೋರಿಸಿ",
        ]),
        ("stk_rw_knr_1", "check_stock", "kn_rom", [
            "dolo 650 innu eshtu tablet ide",
            "metformin balance eshtu ulidide",
        ]),
        ("stk_rw_knr_2", "check_stock", "kn_rom", [
            "maneli eshtu goli ulidide heli",
            "syrup bottle alli eshtu ml stock ide",
        ]),
        ("stk_rw_hi_1", "check_stock", "hi", [
            "डोलो की कितनी गोलियां बची हैं",
            "मेटफॉर्मिन का कितना स्टॉक बचा है",
        ]),
        ("stk_rw_hi_2", "check_stock", "hi", [
            "मेरे पास अभी कितनी दवा बाकी है",
            "सिरप की बोतल में कितनी दवा बची है",
        ]),
        ("stk_rw_hi_3", "check_stock", "hi", [
            "पैन डी कैप्सूल का स्टॉक बताओ",
            "घर में कितनी टैबलेट बची हैं गिन के बताओ",
        ]),
        ("stk_rw_hir_1", "check_stock", "hi_rom", [
            "dolo ki kitni goli bachi hai",
            "pan d capsules ka kitna balance hai",
        ]),
        ("stk_rw_hir_2", "check_stock", "hi_rom", [
            "abhi mere paas kitni medicine bachi h",
            "syrup kitna ml bacha hua hai",
        ]),
        ("stk_rw_cs_1", "check_stock", "code_switch", [
            "dolo 650 kitni left hain stock mein",
            "metformin tablet balance eshtu ide",
        ]),

        # ================= REAL-WORLD EXPANSION: today_schedule =================
        ("tod_rw_en_1", "today_schedule", "en", [
            "what do i take tonight before sleep",
            "show my morning and evening tablets for today",
        ]),
        ("tod_rw_en_2", "today_schedule", "en", [
            "read out today's medication routine",
            "any pills scheduled for this afternoon",
        ]),
        ("tod_rw_en_3", "today_schedule", "en", [
            "what medicines are on my schedule right now",
            "open today timetable",
        ]),
        ("tod_rw_kn_1", "today_schedule", "kn", [
            "ಇಂದು ಬೆಳಗ್ಗೆ ಮತ್ತು ರಾತ್ರಿ ಯಾವ ಔಷಧಿ ಇದೆ",
            "ಇವತ್ತು ಸಂಜೆ ಯಾವ ಮಾತ್ರೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
        ]),
        ("tod_rw_kn_2", "today_schedule", "kn", [
            "ನನ್ನ ಇಂದಿನ ಔಷಧಿ ವೇಳಾಪಟ್ಟಿ ಓದಿ ಹೇಳಿ",
            "ಇಂದು ಮಧ್ಯಾಹ್ನ ಯಾವ ಗುಳಿಗೆ ಇದೆ",
        ]),
        ("tod_rw_knr_1", "today_schedule", "kn_rom", [
            "ivattu ratri yav tablet togobeku",
            "today afternoon yava medicine ide",
        ]),
        ("tod_rw_knr_2", "today_schedule", "kn_rom", [
            "nanna daily tablet list helu",
            "ivattu beligge yava matre ide",
        ]),
        ("tod_rw_hi_1", "today_schedule", "hi", [
            "आज रात सोने से पहले कौन सी गोली लेनी है",
            "आज दोपहर में कौन सी दवाई खानी है",
        ]),
        ("tod_rw_hi_2", "today_schedule", "hi", [
            "मेरा आज का पूरा दवाई प्लान बताइए",
            "आज शाम की दवाइयों की लिस्ट पढ़कर सुनाओ",
        ]),
        ("tod_rw_hir_1", "today_schedule", "hi_rom", [
            "aaj raat ko kaun si tablet leni hai",
            "aaj dopahar mein kya dawai hai",
        ]),
        ("tod_rw_hir_2", "today_schedule", "hi_rom", [
            "aaj ka poora medication plan batao",
            "subah aur raat ki kaunsi goli hai aaj",
        ]),
        ("tod_rw_cs_1", "today_schedule", "code_switch", [
            "today morning aur night ki medicine list dikhao",
            "ivattu night yava pills tagobeku",
        ]),

        # ================= REAL-WORLD EXPANSION: next_dose =================
        ("nxt_rw_en_1", "next_dose", "en", [
            "what is my upcoming pill reminder",
            "when do i need to take dolo next",
        ]),
        ("nxt_rw_en_2", "next_dose", "en", [
            "how long until my next tablet",
            "tell me the time of my next dose",
        ]),
        ("nxt_rw_kn_1", "next_dose", "kn", [
            "ನನ್ನ ಮುಂದಿನ ಡೋಲೋ ಮಾತ್ರೆ ಯಾವಾಗ ಇದೆ",
            "ಮುಂದಿನ ಡೋಸ್ ಇನ್ನು ಎಷ್ಟು ಹೊತ್ತಿಗೆ ಇದೆ",
        ]),
        ("nxt_rw_kn_2", "next_dose", "kn", [
            "ಯಾವ ಸಮಯಕ್ಕೆ ಮುಂದಿನ ಗುಳಿಗೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
            "ಮುಂದಿನ ಔಷಧಿ ಸಮಯವನ್ನು ತಿಳಿಸಿ",
        ]),
        ("nxt_rw_knr_1", "next_dose", "kn_rom", [
            "mundina dolo tablet yavaga togobeku",
            "innu eshtu hottige next dose ide",
        ]),
        ("nxt_rw_hi_1", "next_dose", "hi", [
            "मेरी अगली डोलो गोली कितने बजे है",
            "अगली खुराक में कितना समय बाकी है",
        ]),
        ("nxt_rw_hi_2", "next_dose", "hi", [
            "अगला रिमाइंडर कितने बजे का लगा है",
            "मुझे अगली बार दवाई कब खानी होगी",
        ]),
        ("nxt_rw_hir_1", "next_dose", "hi_rom", [
            "agli dolo tablet kitne baje leni hai",
            "next dose mein kitna time bacha hai",
        ]),
        ("nxt_rw_cs_1", "next_dose", "code_switch", [
            "mera next dose dolo ka kab hai",
            "mundina dose time eshtu baje ide",
        ]),

        # ================= REAL-WORLD EXPANSION: medicine_info =================
        ("inf_rw_en_1", "medicine_info", "en", [
            "tell me about dolo 650 tablet",
            "what are the uses of metformin",
        ]),
        ("inf_rw_en_2", "medicine_info", "en", [
            "does pan d have side effects",
            "precautions for taking paracetamol",
        ]),
        ("inf_rw_kn_1", "medicine_info", "kn", [
            "ಡೋಲೋ ಮಾತ್ರೆಯ ಉಪಯೋಗ ಏನು",
            "ಪ್ಯಾನ್ ಡಿ ಕ್ಯಾಪ್ಸುಲ್ ಅಡ್ಡಪರಿಣಾಮಗಳು ಏನು",
        ]),
        ("inf_rw_kn_2", "medicine_info", "kn", [
            "ಮೆಟ್ಫಾರ್ಮಿನ್ ಔಷಧಿ ಬಗ್ಗೆ ವಿವರಿಸಿ",
            "ಈ ಔಷಧಿ ತೆಗೆದುಕೊಳ್ಳುವ ಮುನ್ನ ಏನು ಎಚ್ಚರಿಕೆ ವಹಿಸಬೇಕು",
        ]),
        ("inf_rw_knr_1", "medicine_info", "kn_rom", [
            "dolo 650 uses mattu side effects heli",
            "metformin yavudakke kodtare heli",
        ]),
        ("inf_rw_hi_1", "medicine_info", "hi", [
            "डोलो 650 टैबलेट किस काम आती है",
            "मेटफॉर्मिन के साइड इफेक्ट और सावधानियां बताइए",
        ]),
        ("inf_rw_hi_2", "medicine_info", "hi", [
            "पैन डी कैप्सूल के बारे में पूरी जानकारी दें",
            "यह दवा लेने से क्या नुकसान हो सकता है",
        ]),
        ("inf_rw_hir_1", "medicine_info", "hi_rom", [
            "dolo 650 kis kaam aati hai aur side effects kya hain",
            "metformin ki precautions bataiye",
        ]),
        ("inf_rw_cs_1", "medicine_info", "code_switch", [
            "pan d ke side effects aur uses batao",
            "dolo tablet bagge verified info torisi",
        ]),

        # ================= REAL-WORLD EXPANSION: adherence_status =================
        ("adh_rw_en_1", "adherence_status", "en", [
            "did i take dolo this morning",
            "have i confirmed my afternoon pill yet",
        ]),
        ("adh_rw_en_2", "adherence_status", "en", [
            "was my breakfast dose taken or skipped",
            "how many doses did i confirm today",
        ]),
        ("adh_rw_kn_1", "adherence_status", "kn", [
            "ಇಂದು ಬೆಳಗ್ಗೆ ನಾನು ಡೋಲೋ ತೆಗೆದುಕೊಂಡೆನಾ",
            "ನನ್ನ ಇಂದಿನ ಡೋಸ್ ಕನ್ಫರ್ಮ್ ಆಗಿದೆಯಾ ನೋಡಿ",
        ]),
        ("adh_rw_kn_2", "adherence_status", "kn", [
            "ರಾತ್ರಿಯ ಔಷಧಿ ತೆಗೆದುಕೊಂಡಿದ್ದೇನಾ ಅಥವಾ ಬಾಕಿ ಇದೆಯಾ",
            "ಇವತ್ತು ಯಾವುದಾದರೂ ಡೋಸ್ ಮಿಸ್ ಆಗಿದೆಯಾ",
        ]),
        ("adh_rw_knr_1", "adherence_status", "kn_rom", [
            "naanu beligge dolo togondidna",
            "ivattu dose confirm agidya illa skip agidya",
        ]),
        ("adh_rw_hi_1", "adherence_status", "hi", [
            "क्या मैंने आज सुबह डोलो खा ली है",
            "आज की कितनी डोज़ कन्फर्म हो चुकी हैं",
        ]),
        ("adh_rw_hi_2", "adherence_status", "hi", [
            "मेरी दोपहर वाली दवाई ली गई या छूटी है",
            "क्या आज मैंने कोई दवाई मिस की है",
        ]),
        ("adh_rw_hir_1", "adherence_status", "hi_rom", [
            "kya maine subah dolo liya tha",
            "aaj ki kitni dose mark ho gayi hain",
        ]),
        ("adh_rw_cs_1", "adherence_status", "code_switch", [
            "morning dolo dose confirm agidya check maadi",
            "did i confirm sham ki tablet today",
        ]),

        # ================= REAL-WORLD EXPANSION: refill_check =================
        ("ref_rw_en_1", "refill_check", "en", [
            "when will my dolo strip finish",
            "do i need to buy more metformin soon",
        ]),
        ("ref_rw_en_2", "refill_check", "en", [
            "check refill prediction for my medicines",
            "when does my medicine run empty",
        ]),
        ("ref_rw_kn_1", "refill_check", "kn", [
            "ಡೋಲೋ ಮಾತ್ರೆ ಯಾವಾಗ ಮುಗಿಯುತ್ತದೆ",
            "ಯಾವ ಔಷಧಿಯನ್ನು ಬೇಗ ರೀಫಿಲ್ ಮಾಡಿಸಬೇಕು",
        ]),
        ("ref_rw_kn_2", "refill_check", "kn", [
            "ಮೆಟ್ಫಾರ್ಮಿನ್ ಇನ್ನು ಎಷ್ಟು ದಿನ ಸಾಕಾಗುತ್ತದೆ",
            "ಹೊಸ ಸ್ಟ್ರಿಪ್ ತರಬೇಕಾದ ದಿನಾಂಕ ಯಾವಾಗ",
        ]),
        ("ref_rw_knr_1", "refill_check", "kn_rom", [
            "dolo strip yavaga mugiyutte",
            "yava medicine bega refill madbeku",
        ]),
        ("ref_rw_hi_1", "refill_check", "hi", [
            "डोलो की पट्टी कब खत्म होगी",
            "कौन सी दवाई जल्दी रीफिल करवानी है",
        ]),
        ("ref_rw_hi_2", "refill_check", "hi", [
            "मेटफॉर्मिन कितने दिन और चलेगी",
            "दवाई खत्म होने की तारीख क्या है",
        ]),
        ("ref_rw_hir_1", "refill_check", "hi_rom", [
            "dolo kab tak chalegi aur refill kab karna hai",
            "kaunsi dawai jaldi khatam hone wali hai",
        ]),
        ("ref_rw_cs_1", "refill_check", "code_switch", [
            "metformin refill alert kab hai check maadi",
            "dolo kitne days aur last karegi",
        ]),

        # ================= REAL-WORLD EXPANSION: confirm_dose =================
        ("cnf_rw_en_1", "confirm_dose", "en", [
            "i took my dolo tablet just now",
            "mark dolo morning dose as taken",
        ]),
        ("cnf_rw_en_2", "confirm_dose", "en", [
            "just had my metformin pill confirm it",
            "log two tablets of paracetamol as taken",
        ]),
        ("cnf_rw_kn_1", "confirm_dose", "kn", [
            "ನಾನು ಈಗಷ್ಟೇ ಡೋಲೋ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆ",
            "ಬೆಳಗಿನ ಮೆಟ್ಫಾರ್ಮಿನ್ ಡೋಸ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ಮಾರ್ಕ್ ಮಾಡಿ",
        ]),
        ("cnf_rw_kn_2", "confirm_dose", "kn", [
            "ರಾತ್ರಿ ಗುಳಿಗೆ ತಿಂದೆ ಕನ್ಫರ್ಮ್ ಮಾಡಿ",
            "ನಾನು ಔಷಧಿ ಕುಡಿದಿದ್ದೇನೆ ಸೇವ್ ಮಾಡಿ",
        ]),
        ("cnf_rw_knr_1", "confirm_dose", "kn_rom", [
            "dolo tablet togonde confirm maadi",
            "metformin morning goli togonde mark maadi",
        ]),
        ("cnf_rw_hi_1", "confirm_dose", "hi", [
            "मैंने अभी डोलो की गोली खा ली है",
            "मेरी सुबह की मेटफॉर्मिन डोज़ कन्फर्म कर दो",
        ]),
        ("cnf_rw_hi_2", "confirm_dose", "hi", [
            "दवाई पी ली है आज की मार्क कर दीजिए",
            "रात की गोली ले ली है अपडेट कर दो",
        ]),
        ("cnf_rw_hir_1", "confirm_dose", "hi_rom", [
            "maine abhi dolo kha li hai confirm karo",
            "morning metformin le li mark taken kar do",
        ]),
        ("cnf_rw_cs_1", "confirm_dose", "code_switch", [
            "dolo morning tablet togonde mark taken karo",
            "just took pan d capsule confirm maadi",
        ]),

        # ================= REAL-WORLD EXPANSION: update_stock_purchase =================
        ("pur_rw_en_1", "update_stock_purchase", "en", [
            "i bought two strips of dolo add to stock",
            "purchased one new pack of metformin",
        ]),
        ("pur_rw_en_2", "update_stock_purchase", "en", [
            "add twenty tablets of paracetamol to inventory",
            "restocked a fresh strip from pharmacy",
        ]),
        ("pur_rw_kn_1", "update_stock_purchase", "kn", [
            "ಎರಡು ಸ್ಟ್ರಿಪ್ ಡೋಲೋ ಖರೀದಿಸಿದ್ದೇನೆ ಸ್ಟಾಕ್ ಸೇರಿಸಿ",
            "ಒಂದು ಹೊಸ ಪ್ಯಾಕ್ ಮೆಟ್ಫಾರ್ಮಿನ್ ತಂದಿದ್ದೇನೆ ಅಪ್ಡೇಟ್ ಮಾಡಿ",
        ]),
        ("pur_rw_kn_2", "update_stock_purchase", "kn", [
            "ಹತ್ತು ಗುಳಿಗೆ ಅಂಗಡಿಯಿಂದ ತಂದೆ ಸ್ಟಾಕ್ ಹಾಕಿ",
            "ಹೊಸ ಸಿರಪ್ ಬಾಟಲ್ ಸ್ಟಾಕ್‌ಗೆ ಸೇರಿಸಿ",
        ]),
        ("pur_rw_knr_1", "update_stock_purchase", "kn_rom", [
            "eradu strip dolo tandini stock add maadi",
            "ondu hosa metformin pack buy madide serisi",
        ]),
        ("pur_rw_hi_1", "update_stock_purchase", "hi", [
            "मैंने डोलो के दो पत्ते खरीदे हैं स्टॉक में जोड़ो",
            "मेटफॉर्मिन की एक नई स्ट्रिप लाया हूं अपडेट करो",
        ]),
        ("pur_rw_hi_2", "update_stock_purchase", "hi", [
            "फार्मेसी से बीस गोलियां खरीदी हैं इन्वेंटरी बढ़ाओ",
            "नई दवा का पैक स्टॉक में डाल दो",
        ]),
        ("pur_rw_hir_1", "update_stock_purchase", "hi_rom", [
            "maine dolo ki do patti kharidi hai stock update karo",
            "ek strip metformin laya hoon add karo",
        ]),
        ("pur_rw_cs_1", "update_stock_purchase", "code_switch", [
            "bought 2 strips of dolo stock update maadi",
            "ek naya pack pan d kharida inventory mein add karo",
        ]),

        # ================= REAL-WORLD EXPANSION: out_of_scope =================
        ("oos_rw_en_1", "out_of_scope", "en", [
            "set an alarm for five pm for office meeting",
            "what is the capital of karnataka",
        ]),
        ("oos_rw_en_2", "out_of_scope", "en", [
            "can you send an email to my friend",
            "translate good morning to french",
        ]),
        ("oos_rw_kn_1", "out_of_scope", "kn", [
            "ಬೆಂಗಳೂರು ಟ್ರಾಫಿಕ್ ಹೇಗಿದೆ ಹೇಳಿ",
            "ಒಂದು ಒಳ್ಳೆಯ ಸಿನಿಮಾ ಹೆಸರು ಹೇಳಿ",
        ]),
        ("oos_rw_knr_1", "out_of_scope", "kn_rom", [
            "bengaluru weather mattu traffic hege ide",
            "ondu olle kannada movie suggest maadi",
        ]),
        ("oos_rw_hi_1", "out_of_scope", "hi", [
            "दिल्ली का मौसम कैसा है आज",
            "मुझे एक अच्छी फिल्म का नाम बताओ",
        ]),
        ("oos_rw_hir_1", "out_of_scope", "hi_rom", [
            "aaj ka news headline sunao",
            "mere liye pizza order kar do",
        ]),

        # ================= REAL-WORLD BALANCING: adherence_status vs confirm_dose =================
        ("adh_rw_q_en_1", "adherence_status", "en", [
            "check whether i already took my morning dose",
            "did i confirm today's pill already or not",
        ]),
        ("adh_rw_q_kn_1", "adherence_status", "kn", [
            "ನಾನು ಬೆಳಗ್ಗೆ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡಿದ್ದೇನಾ ಇಲ್ಲವಾ ಹೇಳಿ",
            "ಇವತ್ತಿನ ಟ್ಯಾಬ್ಲೆಟ್ ತಗೊಂಡಿದೀನಾ ಚೆಕ್ ಮಾಡಿ",
        ]),
        ("adh_rw_q_hi_1", "adherence_status", "hi", [
            "क्या आज की गोली खा ली गई है या बाकी है",
            "चेक करके बताओ मैंने सुबह दवाई ली थी क्या",
        ]),
        ("cnf_rw_imp_kn_1", "confirm_dose", "kn", [
            "ಬೆಳಗಿನ ಡೋಸ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ದಯವಿಟ್ಟು ಸೇವ್ ಮಾಡಿ",
            "ಈಗ ಮಾತ್ರೆ ನುಂಗಿದ್ದೇನೆ ಕನ್ಫರ್ಮ್ ಮಾಡಿ",
        ]),
        ("cnf_rw_imp_hi_1", "confirm_dose", "hi", [
            "मैंने दवाई निगल ली है अभी कन्फर्म कीजिए",
            "सुबह की टैबलेट खाई अभी रिकॉर्ड कर दो",
        ]),

        # ================= REAL-WORLD BALANCING: out_of_scope (EN / KN / HI) =================
        ("oos_bal_en_1", "out_of_scope", "en", [
            "who is the prime minister of india",
            "tell me the latest sports news",
        ]),
        ("oos_bal_en_2", "out_of_scope", "en", [
            "how to cook masala dosa at home",
            "open youtube and play relaxing music",
        ]),
        ("oos_bal_en_3", "out_of_scope", "en", [
            "what is the stock price of infosys today",
            "book a train ticket from bengaluru to mysuru",
        ]),
        ("oos_bal_kn_1", "out_of_scope", "kn", [
            "ಮೈಸೂರು ದಸರಾ ಯಾವಾಗ ಶುರುವಾಗುತ್ತದೆ",
            "ನನಗೆ ಒಳ್ಳೆಯ ಕಥೆ ಹೇಳಿ",
        ]),
        ("oos_bal_kn_2", "out_of_scope", "kn", [
            "ಬೆಂಗಳೂರಿನಿಂದ ಮಂಗಳೂರಿಗೆ ಬಸ್ ಟಿಕೆಟ್ ಬುಕ್ ಮಾಡಿ",
            "ಇಂದಿನ ಚಿನ್ನದ ಬೆಲೆ ಎಷ್ಟಿದೆ",
        ]),
        ("oos_bal_kn_3", "out_of_scope", "kn", [
            "ಕಾಫಿ ಮಾಡುವ ವಿಧಾನ ಹೇಳಿ",
            "ಇಂದು ಪೆಟ್ರೋಲ್ ಬೆಲೆ ಎಷ್ಟು",
        ]),
        ("oos_bal_knr_1", "out_of_scope", "kn_rom", [
            "mysuru road traffic hege ide ivattu",
            "olle hotel hesaru heli dinner ge",
        ]),
        ("oos_bal_hi_1", "out_of_scope", "hi", [
            "भारत के प्रधानमंत्री कौन हैं",
            "आज सोने का भाव क्या चल रहा है",
        ]),
        ("oos_bal_hi_2", "out_of_scope", "hi", [
            "चाय बनाने की रेसिपी बताओ",
            "मुंबई के लिए ट्रेन टिकट बुक कर दो",
        ]),
        ("oos_bal_hi_3", "out_of_scope", "hi", [
            "आज की ताजा खबरें पढ़कर सुनाओ",
            "मुझे एक चुटकुला सुनाओ",
        ]),
        ("oos_bal_hir_1", "out_of_scope", "hi_rom", [
            "train ticket book kar do delhi ke liye",
            "aaj petrol ka rate kya hai batao",
        ]),

        # ================= VOICE SHORT-COMMAND & INDIC PARAPHRASE EXPANSION =================
        ("stk_v_en_1", "check_stock", "en", [
            "stock check",
            "check inventory",
            "remaining pills",
        ]),
        ("stk_v_kn_1", "check_stock", "kn", [
            "ನನ್ನಲ್ಲಿ ಬಾಕಿ ಎಷ್ಟಿದೆ ನೋಡಿ",
            "ಸ್ಟಾಕ್ ಬ್ಯಾಲೆನ್ಸ್ ಚೆಕ್ ಮಾಡಿ",
            "ಔಷಧಿ ಸ್ಟಾಕ್ ತೋರಿಸಿ",
        ]),
        ("stk_v_hi_1", "check_stock", "hi", [
            "बचा हुआ स्टॉक चेक करो",
            "कितनी दवा बाकी बची है",
            "स्टॉक बैलेंस दिखाओ",
        ]),
        ("tod_v_en_1", "today_schedule", "en", [
            "today schedule",
            "todays pills",
            "show today doses",
        ]),
        ("tod_v_kn_1", "today_schedule", "kn", [
            "ಇಂದಿನ ಮಾತ್ರೆಗಳ ಪಟ್ಟಿ ಹೇಳಿ",
            "ಇವತ್ತು ಯಾವ ಯಾವ ಮಾತ್ರೆ ಇದೆ",
            "ಇಂದಿನ ಶೆಡ್ಯೂಲ್ ಓದಿ",
        ]),
        ("tod_v_hi_1", "today_schedule", "hi", [
            "आज की दवाई की लिस्ट बताओ",
            "आज क्या क्या खाना है दवा में",
            "आज का शेड्यूल सुनाओ",
        ]),
        ("nxt_v_en_1", "next_dose", "en", [
            "next dose",
            "next medicine time",
            "when is next pill",
        ]),
        ("nxt_v_kn_1", "next_dose", "kn", [
            "ಮುಂದಿನ ಡೋಸ್ ಯಾವಾಗ",
            "ಮುಂದಿನ ಮಾತ್ರೆ ಟೈಮ್ ತಿಳಿಸಿ",
            "ಇನ್ನು ಯಾವಾಗ ಔಷಧಿ ತೆಗೆದುಕೊಳ್ಳಬೇಕು",
        ]),
        ("nxt_v_hi_1", "next_dose", "hi", [
            "अगली डोज़ कब लेनी है",
            "नेक्स्ट दवाई कितने बजे है",
            "अगली गोली का टाइम बताओ",
        ]),
        ("inf_v_en_1", "medicine_info", "en", [
            "medicine information",
            "side effects of this pill",
            "what is dolo used for",
        ]),
        ("inf_v_kn_1", "medicine_info", "kn", [
            "ಈ ಔಷಧಿಯ ವಿವರ ಹೇಳಿ",
            "ಮಾತ್ರೆಯ ಅಡ್ಡಪರಿಣಾಮ ಏನು",
            "ಡೋಲೋ ಯಾವುದಕ್ಕೆ ಬಳಸುತ್ತಾರೆ",
        ]),
        ("inf_v_hi_1", "medicine_info", "hi", [
            "इस दवा के बारे में जानकारी चाहिए",
            "दवाई के साइड इफेक्ट बताओ",
            "यह गोली किस बीमारी में काम आती है",
        ]),
        ("adh_v_en_1", "adherence_status", "en", [
            "did i take today dose",
            "today adherence status",
            "check if morning tablet taken",
        ]),
        ("adh_v_kn_1", "adherence_status", "kn", [
            "ಇಂದು ನಾನು ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆನಾ",
            "ಇಂದಿನ ಡೋಸ್ ತಗೊಂಡಿದೀನಾ ನೋಡಿ",
            "ನನ್ನ ಇಂದಿನ ಅನುಸರಣಾ ಸ್ಥಿತಿ ತೋರಿಸಿ",
        ]),
        ("adh_v_hi_1", "adherence_status", "hi", [
            "क्या मैंने आज दवाई खा ली है",
            "सुबह की खुराक ली गई या नहीं",
            "मेरा आज का डोज़ स्टेटस दिखाओ",
        ]),
        ("ref_v_en_1", "refill_check", "en", [
            "refill check",
            "when do i need to refill",
            "how many days supply left",
        ]),
        ("ref_v_kn_1", "refill_check", "kn", [
            "ರಿಫಿಲ್ ಯಾವಾಗ ಮಾಡಬೇಕು",
            "ಮಾತ್ರೆಗಳು ಯಾವಾಗ ಮುಗಿಯುತ್ತವೆ",
            "ಇನ್ನು ಎಷ್ಟು ದಿನ ಸ್ಟಾಕ್ ಬರುತ್ತದೆ",
        ]),
        ("ref_v_hi_1", "refill_check", "hi", [
            "दवाई कब रीफिल करानी पड़ेगी",
            "मेरा स्टॉक कब खत्म हो जाएगा",
            "दवा कितने दिन और चल जाएगी",
        ]),
        ("cnf_v_en_1", "confirm_dose", "en", [
            "confirm morning dose",
            "mark dolo taken",
            "i took my pill now",
        ]),
        ("cnf_v_kn_1", "confirm_dose", "kn", [
            "ಈಗ ಮಾತ್ರೆ ತೆಗೆದುಕೊಂಡೆ ಕನ್ಫರ್ಮ್ ಮಾಡಿ",
            "ಬೆಳಗಿನ ಮಾತ್ರೆ ತಗೊಂಡೆ ಗುರುತಿಸಿ",
            "ಡೋಸ್ ತೆಗೆದುಕೊಂಡಿದ್ದೇನೆ ಸೇವ್ ಮಾಡಿ",
        ]),
        ("cnf_v_hi_1", "confirm_dose", "hi", [
            "मैंने दवाई खा ली कन्फर्म कर दो",
            "सुबह की गोली ले ली मार्क करो",
            "मेरी डोज़ ली गई है सेव कर दो",
        ]),
        ("pur_v_en_1", "update_stock_purchase", "en", [
            "add one strip",
            "bought two packs update stock",
            "purchased ten tablets",
        ]),
        ("pur_v_kn_1", "update_stock_purchase", "kn", [
            "ಹೊಸ ಸ್ಟ್ರಿಪ್ ತಂದಿದ್ದೇನೆ ಸ್ಟಾಕ್ ಸೇರಿಸಿ",
            "ಎರಡು ಪ್ಯಾಕ್ ಖರೀದಿಸಿದ್ದೇನೆ ಅಪ್ಡೇಟ್ ಮಾಡಿ",
            "ಹತ್ತು ಮಾತ್ರೆಗಳನ್ನು ಸ್ಟಾಕ್‌ಗೆ ಹಾಕಿ",
        ]),
        ("pur_v_hi_1", "update_stock_purchase", "hi", [
            "नया पत्ता खरीदा है स्टॉक जोड़ दो",
            "दो स्ट्रिप लाया हूं इन्वेंटरी बढ़ाओ",
            "दस गोलियां स्टॉक में ऐड करो",
        ]),
        ("oos_v_en_1", "out_of_scope", "en", [
            "tell me a story",
            "call mom on phone",
            "open settings app",
        ]),
        ("oos_v_kn_1", "out_of_scope", "kn", [
            "ಇಂದಿನ ರಾಶಿ ಭವಿಷ್ಯ ಹೇಳಿ",
            "ಕನ್ನಡ ಹಾಡು ಹಾಕಿ",
            "ಬೆಂಗಳೂರಿನಲ್ಲಿ ಎಷ್ಟು ಗಂಟೆ ಆಯಿತು",
        ]),
        ("oos_v_hi_1", "out_of_scope", "hi", [
            "आज का राशिफल बताओ",
            "बॉलीवुड गाना बजाओ",
            "दिल्ली में अभी कितने बजे हैं",
        ]),
        ("oos_v_knr_1", "out_of_scope", "kn_rom", [
            "karnataka weather report heli",
            "bengaluru cricket score yenu",
        ]),
        ("oos_v_hir_1", "out_of_scope", "hi_rom", [
            "mumbai ka mausam kaisa hai",
            "cricket match ka score batao",
        ]),

        # ================= 10. company_lookup =================
        ("cmp_en_1", "company_lookup", "en", [
            "which company makes dolo 650",
            "who manufactures metformin tablets",
        ]),
        ("cmp_en_2", "company_lookup", "en", [
            "i only know the company name cipla show medicines",
            "find tablets made by micro labs",
        ]),
        ("cmp_en_3", "company_lookup", "en", [
            "i forgot the tablet name show sun pharma products",
            "search medicines manufactured by glenmark",
        ]),
        ("cmp_en_4", "company_lookup", "en", [
            "list verified drugs from dr reddys laboratory",
            "show me tablets by abbott pharma",
        ]),
        ("cmp_en_5", "company_lookup", "en", [
            "what manufacturer produces this medicine",
            "which pharma brand sells these capsules",
        ]),
        ("cmp_kn_1", "company_lookup", "kn", [
            "ಈ ಮಾತ್ರೆಯನ್ನು ಯಾವ ಕಂಪನಿ ತಯಾರಿಸುತ್ತದೆ",
            "ಸಿಪ್ಲಾ ಕಂಪನಿಯ ಔಷಧಿಗಳನ್ನು ತೋರಿಸಿ",
        ]),
        ("cmp_kn_2", "company_lookup", "kn", [
            "ಮೈಕ್ರೋ ಲ್ಯಾಬ್ಸ್ ಕಂಪನಿಯ ಮಾತ್ರೆಗಳು ಯಾವುವು",
            "ನನಗೆ ಕಂಪನಿ ಹೆಸರು ಮಾತ್ರ ಗೊತ್ತು ಔಷಧಿ ಹುಡುಕಿ",
        ]),
        ("cmp_kn_3", "company_lookup", "kn", [
            "ಸನ್ ಫಾರ್ಮಾ ಕಂಪನಿಯ ಟ್ಯಾಬ್ಲೆಟ್ ಪಟ್ಟಿ ತೋರಿಸಿ",
            "ಗ್ಲೆನ್ಮಾರ್ಕ್ ಕಂಪನಿ ತಯಾರಿಸುವ ಮಾತ್ರೆ ಹುಡುಕಿ",
        ]),
        ("cmp_knr_1", "company_lookup", "kn_rom", [
            "ee tablet yava company madutte",
            "cipla company medicines torisi",
        ]),
        ("cmp_knr_2", "company_lookup", "kn_rom", [
            "micro labs company tablets yavdu ide",
            "company hesaru matra gottu tablet name heli",
        ]),
        ("cmp_knr_3", "company_lookup", "kn_rom", [
            "sun pharma manufacturer medicines search maadi",
            "dr reddys company capsules yavdu",
        ]),
        ("cmp_hi_1", "company_lookup", "hi", [
            "यह दवाई किस कंपनी की है",
            "सिप्ला कंपनी की दवाइयां दिखाओ",
        ]),
        ("cmp_hi_2", "company_lookup", "hi", [
            "मुझे दवाई का नाम नहीं पता सिर्फ कंपनी याद है",
            "सन फार्मा कंपनी की गोलियां खोजो",
        ]),
        ("cmp_hi_3", "company_lookup", "hi", [
            "एबॉट कंपनी की टैबलेट लिस्ट दिखाओ",
            "इस दवा का निर्माता कौन सी कंपनी है",
        ]),
        ("cmp_hir_1", "company_lookup", "hi_rom", [
            "ye tablet kaunsi company banati hai",
            "cipla company ki dawai dikhao",
        ]),
        ("cmp_hir_2", "company_lookup", "hi_rom", [
            "sirf company ka naam pata hai sun pharma ki dawai batao",
            "micro labs manufacturer ki tablets search karo",
        ]),
        ("cmp_cs_1", "company_lookup", "code_switch", [
            "dolo 650 ka manufacturer company kya hai heli",
            "sun pharma company tablets search maadi",
        ]),
        ("cmp_cs_2", "company_lookup", "code_switch", [
            "cipla manufacturer medicines list madu",
            "company name matra gottu tablet search karo",
        ]),

        # ================= 11. skip_dose =================
        ("skp_en_1", "skip_dose", "en", [
            "skip my afternoon tablet",
            "mark my morning dose as skipped",
        ]),
        ("skp_en_2", "skip_dose", "en", [
            "i want to skip dolo today evening",
            "please skip my current scheduled pill",
        ]),
        ("skp_en_3", "skip_dose", "en", [
            "skipping this dose because i forgot earlier",
            "set todays night capsule as skipped",
        ]),
        ("skp_en_4", "skip_dose", "en", [
            "mark current reminder skipped",
            "do not count this evening tablet skip it",
        ]),
        ("skp_kn_1", "skip_dose", "kn", [
            "ಇಂದಿನ ಮಧ್ಯಾಹ್ನದ ಮಾತ್ರೆ ಸ್ಕಿಪ್ ಮಾಡಿ",
            "ಬೆಳಗಿನ ಡೋಸ್ ಸ್ಕಿಪ್ ಎಂದು ಗುರುತಿಸಿ",
        ]),
        ("skp_kn_2", "skip_dose", "kn", [
            "ಸಂಜೆಯ ಟ್ಯಾಬ್ಲೆಟ್ ತೆಗೆದುಕೊಳ್ಳುತ್ತಿಲ್ಲ ಸ್ಕಿಪ್ ಮಾಡಿ",
            "ಇವತ್ತಿನ ಡೋಸ್ ಸ್ಕಿಪ್ ಮಾಡಿ ಸೇವ್ ಮಾಡಿ",
        ]),
        ("skp_kn_3", "skip_dose", "kn", [
            "ಈಗಿನ ಮಾತ್ರೆ ಸ್ಕಿಪ್ ಎಂದು ನಮೂದಿಸಿ",
            "ರಾತ್ರಿಯ ಗುಳಿಗೆ ಬಿಟ್ಟುಬಿಡಿ ಸ್ಕಿಪ್ ಮಾಡಿ",
        ]),
        ("skp_knr_1", "skip_dose", "kn_rom", [
            "ivattina afternoon tablet skip maadi",
            "morning dose skip antha mark maadi",
        ]),
        ("skp_knr_2", "skip_dose", "kn_rom", [
            "evening gulige skip madbeku save maadi",
            "current dose skip madidini mark maadi",
        ]),
        ("skp_hi_1", "skip_dose", "hi", [
            "आज दोपहर की गोली स्किप कर दो",
            "मेरी शाम की दवाई को छोड़ा गया मार्क करो",
        ]),
        ("skp_hi_2", "skip_dose", "hi", [
            "मैं अभी वाली डोज़ स्किप करना चाहता हूं",
            "सुबह की टैबलेट स्किप कर दीजिए",
        ]),
        ("skp_hi_3", "skip_dose", "hi", [
            "रात की खुराक स्किप के रूप में सेव करो",
            "आज की डोज छोड़नी है स्किप मार्क करो",
        ]),
        ("skp_hir_1", "skip_dose", "hi_rom", [
            "aaj sham ki goli skip kar do",
            "meri current dose skip mark karo",
        ]),
        ("skp_hir_2", "skip_dose", "hi_rom", [
            "morning tablet nahi li skip set karo",
            "is dose ko skipped mark kar do",
        ]),
        ("skp_cs_1", "skip_dose", "code_switch", [
            "evening dolo dose skip maadi please",
            "aaj ki afternoon pill skip kar do",
        ]),
        ("skp_cs_2", "skip_dose", "code_switch", [
            "current medicine dose skip mark maadu",
            "night pill skip karne ka hai please",
        ]),

        # ================= 12. snooze_dose =================
        ("snz_en_1", "snooze_dose", "en", [
            "snooze my dose reminder for 15 minutes",
            "remind me again in 15 minutes",
        ]),
        ("snz_en_2", "snooze_dose", "en", [
            "snooze this medicine alarm for now",
            "delay my tablet reminder by 15 mins",
        ]),
        ("snz_en_3", "snooze_dose", "en", [
            "push my pill notification back 15 minutes",
            "postpone current dose alarm briefly",
        ]),
        ("snz_en_4", "snooze_dose", "en", [
            "ring the dose reminder again later",
            "snooze evening tablet alert",
        ]),
        ("snz_kn_1", "snooze_dose", "kn", [
            "ನನ್ನ ಡೋಸ್ ರಿಮೈಂಡರ್ ಅನ್ನು 15 ನಿಮಿಷ ಮುಂದೂಡಿ",
            "ಸ್ನೂಜ್ ಮಾಡಿ 15 ನಿಮಿಷದ ನಂತರ ನೆನಪಿಸಿ",
        ]),
        ("snz_kn_2", "snooze_dose", "kn", [
            "ಮಾತ್ರೆ ಅಲಾರಾಂ ಸ್ವಲ್ಪ ಹೊತ್ತು ಮುಂದೂಡಿ",
            "15 ನಿಮಿಷ ಬಿಟ್ಟು ಮತ್ತೆ ನೆನಪಿಸಿ",
        ]),
        ("snz_kn_3", "snooze_dose", "kn", [
            "ಈಗಿನ ಔಷಧಿ ಅಲಾರಾಂ ಸ್ನೂಜ್ ಮಾಡಿ",
            "ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಅಲಾರಂ ಹಾಕಿ",
        ]),
        ("snz_knr_1", "snooze_dose", "kn_rom", [
            "dose reminder 15 minutes snooze maadi",
            "innu 15 nimisha bittu matte nenapisi",
        ]),
        ("snz_knr_2", "snooze_dose", "kn_rom", [
            "tablet alarm mundoodi snooze maadu",
            "swalpa hottu bittu alarm matte hakisi",
        ]),
        ("snz_hi_1", "snooze_dose", "hi", [
            "मेरा दवाई रिमाइंडर 15 मिनट के लिए स्नूज़ कर दो",
            "मुझे 15 मिनट बाद फिर से याद दिलाना",
        ]),
        ("snz_hi_2", "snooze_dose", "hi", [
            "अभी के लिए अलार्म थोड़ा आगे बढ़ा दो",
            "डोज़ रिमाइंडर को स्नूज़ कीजिए",
        ]),
        ("snz_hi_3", "snooze_dose", "hi", [
            "दवाई का अलार्म पंद्रह मिनट बाद बजाओ",
            "गोली का रिमाइंडर कुछ देर टाल दो",
        ]),
        ("snz_hir_1", "snooze_dose", "hi_rom", [
            "reminder 15 minute snooze kar do",
            "mujhe 15 min baad yaad dilana",
        ]),
        ("snz_hir_2", "snooze_dose", "hi_rom", [
            "dawai alarm thoda aage badhao snooze karo",
            "abhi wala reminder 15 minutes delay karo",
        ]),
        ("snz_cs_1", "snooze_dose", "code_switch", [
            "dolo reminder 15 minutes snooze maadi",
            "alarm thodi der snooze kar do",
        ]),
        ("snz_cs_2", "snooze_dose", "code_switch", [
            "morning tablet reminder 15 min baad snooze maadu",
            "dose alert 15 mins postpone kar do",
        ]),

        # ================= 13. greeting_help =================
        ("grt_en_1", "greeting_help", "en", [
            "good morning nityamed how are you",
            "hello assistant what can you help me with",
        ]),
        ("grt_en_2", "greeting_help", "en", [
            "tell me all things you can do for me",
            "thank you very much for helping",
        ]),
        ("grt_en_3", "greeting_help", "en", [
            "hi there introduce yourself",
            "good evening can you assist me with my medicines",
        ]),
        ("grt_en_4", "greeting_help", "en", [
            "how does this voice assistant work",
            "show example commands i can ask you",
        ]),
        ("grt_kn_1", "greeting_help", "kn", [
            "ನಮಸ್ಕಾರ ಸಹಾಯಕ ಹೇಗಿದ್ದೀರಾ",
            "ನೀವು ನನಗೆ ಏನು ಸಹಾಯ ಮಾಡಬಲ್ಲಿರಿ",
        ]),
        ("grt_kn_2", "greeting_help", "kn", [
            "ಶುಭೋದಯ ನಿತ್ಯಮೆಡ್ ಧನ್ಯವಾದಗಳು",
            "ನೀವು ಯಾವ ಕೆಲಸಗಳನ್ನು ಮಾಡುತ್ತೀರಿ ತಿಳಿಸಿ",
        ]),
        ("grt_knr_1", "greeting_help", "kn_rom", [
            "namaskara assistant neevu enu help madtira",
            "hello nityamed tumba thanks",
        ]),
        ("grt_knr_2", "greeting_help", "kn_rom", [
            "hi nityamed hegiddira enu madaballiri",
            "nanna sahaya maadalu neevu enu madtira",
        ]),
        ("grt_hi_1", "greeting_help", "hi", [
            "नमस्ते सहायक आप मेरी क्या मदद कर सकते हैं",
            "बहुत बहुत धन्यवाद आपकी सहायता के लिए",
        ]),
        ("grt_hi_2", "greeting_help", "hi", [
            "सुप्रभात नितायमेड आप कैसे हैं",
            "आप किस किस काम में मेरी मदद कर सकते हैं",
        ]),
        ("grt_hir_1", "greeting_help", "hi_rom", [
            "namaste assistant aap kya kya kar sakte ho",
            "hello nityamed kaise madad karoge",
        ]),
        ("grt_hir_2", "greeting_help", "hi_rom", [
            "good morning shukriya madad ke liye",
            "hi assistant tum kya kar sakte ho batao",
        ]),
        ("grt_cs_1", "greeting_help", "code_switch", [
            "hello nityamed enu help madಬಹುದು",
            "hi assistant aap kaise help karte ho heli",
        ]),
        ("grt_en_5", "greeting_help", "en", [
            "hello who is there help me",
            "hi assistant i need help",
        ]),
        ("grt_en_6", "greeting_help", "en", [
            "what commands do you support",
            "thanks a lot nityamed",
        ]),
        ("grt_kn_3", "greeting_help", "kn", [
            "ಹಲೋ ನಿತ್ಯಮೆಡ್ ನನಗೆ ಸಹಾಯ ಬೇಕು",
            "ನೀವು ಏನೆಲ್ಲಾ ಸಹಾಯ ಮಾಡುತ್ತೀರಿ ಹೇಳಿ",
        ]),
        ("grt_hi_3", "greeting_help", "hi", [
            "हेलो नित्यमेड मुझे मदद चाहिए",
            "बताओ तुम मेरी किस तरह सहायता कर सकते हो",
        ]),

        # ================= Voice Short & Natural Everyday Phrasing Boosters =================
        ("v_sch_1", "today_schedule", "en", [
            "today schedule",
            "my medicines today",
        ]),
        ("v_sch_2", "today_schedule", "en", [
            "what pills today",
            "morning schedule list",
        ]),
        ("v_sch_kn_1", "today_schedule", "kn_rom", [
            "ivattu yava matre",
            "today tablet schedule torisi",
        ]),
        ("v_sch_hi_1", "today_schedule", "hi_rom", [
            "aaj ki goli list",
            "aaj ka schedule batao",
        ]),
        ("v_stk_1", "check_stock", "en", [
            "check stock",
            "my tablet balance",
        ]),
        ("v_stk_2", "check_stock", "en", [
            "how many left",
            "remaining tablets dolo",
        ]),
        ("v_stk_kn_1", "check_stock", "kn_rom", [
            "stock check maadi",
            "dolo eshtu ide",
        ]),
        ("v_stk_hi_1", "check_stock", "hi_rom", [
            "stock check karo",
            "kitni goli bachi hai",
        ]),
        ("v_nxt_1", "next_dose", "en", [
            "next dose",
            "when next pill",
        ]),
        ("v_nxt_2", "next_dose", "en", [
            "upcoming medicine time",
            "when should i take next",
        ]),
        ("v_ref_1", "refill_check", "en", [
            "when refill",
            "need to buy soon",
        ]),
        ("v_ref_2", "refill_check", "en", [
            "which medicine running out soon",
            "how many days stock will last",
        ]),
        ("v_ref_kn_1", "refill_check", "kn_rom", [
            "yavaga refill madbeku",
            "inneshtu dina barutte tablet",
        ]),
        ("v_ref_hi_1", "refill_check", "hi_rom", [
            "refill kab lena hai",
            "kitne din aur chalegi dawai",
        ]),
        ("v_cnf_1", "confirm_dose", "en", [
            "took dolo",
            "mark tablet taken",
        ]),
        ("v_cnf_2", "confirm_dose", "en", [
            "i finished morning medicine",
            "just took my dose",
        ]),
        ("v_cmp_1", "company_lookup", "en", [
            "cipla tablets",
            "show micro labs",
        ]),
        ("v_cmp_2", "company_lookup", "en", [
            "which company makes this tablet",
            "find glenmark medicines",
        ]),
        ("v_snz_1", "snooze_dose", "en", [
            "snooze 10 minutes",
            "delay dose 30 mins",
        ]),
        ("v_skp_1", "skip_dose", "en", [
            "skip dolo",
            "skip morning pill",
        ]),
        ("v_inf_1", "medicine_info", "en", [
            "dolo side effects",
            "what is metformin used for",
        ]),
        ("v_adh_1", "adherence_status", "en", [
            "did i take morning dose",
            "my adherence today",
        ]),
        ("v_oos_1", "out_of_scope", "en", [
            "play bollywood music",
            "what is the cricket score",
        ]),
        ("v_oos_2", "out_of_scope", "en", [
            "book a cab to airport",
            "tell me a funny joke",
        ]),
    ]

    samples: list[UtteranceSample] = []
    for family_id, intent, lang_group, texts in families:
        for text in texts:
            samples.append(
                UtteranceSample(
                    text=text.strip(),
                    intent=intent,
                    lang_group=lang_group,
                    family_id=family_id,
                )
            )
    return samples
