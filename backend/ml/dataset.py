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
