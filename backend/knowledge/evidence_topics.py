"""
EVIDENCE TOPIC BANK - Jarvis "Neden X yerine Y?" kanit bankasi (FAZ 7)
========================================================================
Kuratorsel bilimsel cevap bankasi: kullanici bilimsel bir soru sordugunda,
mesajdaki anahtar kelimeler + hareket adlari ile bu tabloda eslesme aranir ve
Jarvis prompt'una küratörlü cevap çekirdeği girer. AI, kanit yapisini (net cevap
+ biyomekanik mekanizma + key_studies) bu çekirdeğin üzerine kurar; PubMed canli
sorgu yalnizca tamamlayicidir.

DIKKAT: PMID'ler üretimden once verify_pmid.py ile dogrulanmalidir (uydurma
atif riski). EVIDENCE_TOPICS icindeki kayitlarda PMID bos ise "verify_pmid.py ile
dogrulanacak" isareti tasidigini unutma.
"""
from __future__ import annotations

# (key_studies: [{authors, year, title, pmid, journal, link}], exercise_reccs: [{exercise, rep_range, rir, head, why}])
EVIDENCE_TOPICS: list[dict] = [
    {
        "topic": "exercise_choice",
        "question_keywords": "triceps,overhead,pushdown,long head,uzun baş,extension,neden bu hareket,neden o hareket,neden pushdown,neden overhead,neden dambıl,neden kablo",
        "muscle_group": "Triceps",
        "focused_exercises": "Overhead Cable Extension,Overhead Dumbbell Extension,Cable Pushdown,Close-Grip Bench,Skull Crusher",
        "direct_answer": (
            "Triceps'in long head'ı omuz ekleminden geçtiği için onu en çok gerilmiş pozisyonda "
            "yükleyen hareketler omuz tam fleksiyondayken yapılanlardır (overhead extension). "
            "Pushdown ise dirsek ekstansiyonunun kısalma ucunda lateral/medial başları çalıştırır; "
            "long-head derinliği için ikisi plan içinde farklı amaçla durur."
        ),
        "biomechanics": (
            "Triceps üç başlıdır; long head skapula kökenlidir ve omuz ekleminde fleksiyona uğrar. "
            "Omuz tam fleksiyondayken long head en uzun gerilmiş pozisyondadır - overhead varyantlar "
            "bu pozisyonda yük verir (lengthened-state overload), pushdown ise long head'ı kısa-orta "
            "pozisyonda tutar. Miyofibriler gerilim en uza pozisyonda en güçlü hipertrofik sinyali üretir."
        ),
        "exercise_reccs": [
            {"exercise": "Overhead Cable Extension", "rep_range": "10-15", "rir": 1, "head": "long_head",
             "why": "Omuz fleksiyonda long head'i tam gerilmiş pozisyonda yükler."},
            {"exercise": "Cable Pushdown", "rep_range": "12-15", "rir": 1, "head": "lateral_head|medial_head",
             "why": "Kısalma ucunda lateral/medial başı izole yükler."},
            {"exercise": "Close-Grip Bench Press", "rep_range": "6-10", "rir": 2, "head": "overall",
             "why": "En yüksek eksternal yükle triceps'e bileşik hacim."},
            {"exercise": "Skull Crusher", "rep_range": "10-12", "rir": 1, "head": "long_head",
             "why": "Omuz fleksiyonda long head'i gerer, dirsek ekstansiyonunu ekler."},
        ],
        "key_studies": [
            {"authors": "Maeo et al.", "year": 2023, "title": "Triceps brachii hypertrophy is substantially greater after elbow extension training performed in the overhead versus neutral arm position",
             "pmid": "35819335", "journal": "Eur J Sport Sci", "link": "https://pubmed.ncbi.nlm.nih.gov/35819335/"},
        ],
        "source_note": "PMID verify_pmid.py ile doğrulanacak; özet literatür konsensüsüne dayanır.",
        "priority": 9,
    },
    {
        "topic": "exercise_choice",
        "question_keywords": "hamstring,seated leg curl,lying leg curl,neden seated,neden oturarak,bacak curl,hamstring izolasyon",
        "muscle_group": "Hamstring & Glute",
        "focused_exercises": "Seated Leg Curl,Lying Leg Curl,Romanian Deadlift,45-Degree Hyperextension",
        "direct_answer": (
            "Seated leg curl, kalça 90° fleksiyondayken çalıştığı için hamstring'i (özellikle "
            "biceps femoris long head) GERİLMİŞ pozisyonda yükler; araştırmalar bu pozisyonun "
            "hipertrofi için lying curl'a belirgin üstün geldiğini gösterdi."
        ),
        "biomechanics": (
            "Biceps femoris long head ve semitendinosus kalça ve dizden geçen çift eklem kaslarıdır. "
            "Seated pozisyon kalça fleksiyonuyla uzun başı gerer ve hareket o gerilmiş pozisyondan "
            "başlar; aynı hacimde seated curl, hamstring hipertrofisinde yalancı varyanttan daha "
            "büyük kazanım verir (lengthened-state etkisi)."
        ),
        "exercise_reccs": [
            {"exercise": "Seated Leg Curl", "rep_range": "10-15", "rir": 1, "head": "biceps_femoris",
             "why": "Lengthened pozisyon; hamstring için en güçlü izolasyon."},
            {"exercise": "Romanian Deadlift", "rep_range": "6-10", "rir": 2, "head": "biceps_femoris",
             "why": "Ağır bileşik; kalça fleksiyonunda uzun başı gerilmiş pozisyonda yükler."},
            {"exercise": "Lying Leg Curl", "rep_range": "10-12", "rir": 1, "head": "semitendinosus",
             "why": "Kısalma ucunda medial baş vurgusu; hacim tamamlayıcısı."},
        ],
        "key_studies": [
            {"authors": "Maeo et al.", "year": 2021, "title": "Greater Hamstrings Muscle Hypertrophy but Similar Damage Protection after Training at Long versus Short Muscle Lengths",
             "pmid": "33009197", "journal": "Med Sci Sports Exerc", "link": "https://pubmed.ncbi.nlm.nih.gov/33009197/"},
        ],
        "source_note": "PMID'ler verify_pmid.py ile doğrulanacak.",
        "priority": 9,
    },
    {
        "topic": "exercise_choice",
        "question_keywords": "göğüs,bench,incline,flat,neden incline,üst göğüs,uc göğüs,upper chest,incline fly,guillotine",
        "muscle_group": "Göğüs",
        "focused_exercises": "Incline Barbell Press,Flat Barbell Press,Incline Dumbbell Fly,Guillotine Press,Low-to-High Cable Fly",
        "direct_answer": (
            "Bench açısı üst göğüs aktivasyonunu ve yük dağılımını değiştirir; 30° civarı incline "
            "varyantlar üst başı hedeflemek için makul bir seçenek, flat varyantlar ise sternal bölge "
            "için tamamlayıcıdır. Fly/cable hareketleri ROM ve kişisel toleransa göre eklenebilir; "
            "tek bir açının herkeste üstün olduğu söylenemez."
        ),
        "biomechanics": (
            "Pectoralis major klavikular (üst) ve sternal (alt) bölümlere ayrılır. Bench açısı "
            "arttıkça üst bölge EMG'si artabilir, ancak bu akut EMG bulgusu doğrudan uzun dönem "
            "hipertrofi üstünlüğü anlamına gelmez. Hareket açıklığı, yüklenebilirlik, omuz toleransı "
            "ve toplam hacim birlikte değerlendirilmelidir."
        ),
        "exercise_reccs": [
            {"exercise": "Incline Barbell Press", "rep_range": "6-10", "rir": 2, "head": "upper",
             "why": "Üst başı en yüksek ağırlıkla yükleyen bileşik."},
            {"exercise": "Incline Dumbbell Fly", "rep_range": "10-15", "rir": 1, "head": "upper",
             "why": "Lengthened-state; üst başa gerilmiş pozisyonda izole gerilim."},
            {"exercise": "Flat Dumbbell Press", "rep_range": "6-10", "rir": 2, "head": "overall",
             "why": "Genel göğüs hacmi için serbest dambıl derinliği."},
        ],
        "key_studies": [
            {"authors": "Rodríguez-Ridao et al.", "year": 2020, "title": "Effect of Five Bench Inclinations on the Electromyographic Activity of the Pectoralis Major, Anterior Deltoid, and Triceps Brachii during the Bench Press Exercise",
             "pmid": "33049982", "journal": "Int J Environ Res Public Health", "link": "https://pubmed.ncbi.nlm.nih.gov/33049982/"},
        ],
        "source_note": "PMID verify_pmid.py ile doğrulanacak.",
        "priority": 8,
    },
    {
        "topic": "exercise_choice",
        "question_keywords": "quad,bacak önü,derin squat,squat derinliği,atl,squat,kısmi squat,partial squat,leg extension,sissy squat",
        "muscle_group": "Quadriceps",
        "focused_exercises": "ATG Back Squat,Front Squat,Hack Squat,Leg Extension,Sissy Squat",
        "direct_answer": (
            "Derin squat, quadriceps'i hem en uzun kas-boyunda hem de en yüksek diz fleksiyonunda "
            "yükler; araştırmalar tam-derinlik squatting'in kısmiye göre quad hipertrofisini belirgin "
            "artırdığını gösterdi. Leg extension ise kısalma ucunda izole diz ekstansör vurgusu için plana girer."
        ),
        "biomechanics": (
            "Quadriceps dört baştan oluşur; derinlik arttıkça diz açısı artar ve kas lifleri uzar. "
            "Tam derinlikte mekanik gerilim artar ve motor ünite rekrütmanı yükselir. Sissy squat "
            "gerilmiş pozisyonda vastus medialis'i izole yükler; leg extension kısalma ucunu tamamlar."
        ),
        "exercise_reccs": [
            {"exercise": "ATG Back Squat", "rep_range": "6-10", "rir": 2, "head": "overall",
             "why": "Derinlikte quad lifleri tam gerilir; en yüksek toplam quad uyarısı."},
            {"exercise": "Sissy Squat", "rep_range": "10-15", "rir": 1, "head": "vastus_medialis",
             "why": "Lengthened-state; medial vastus izolasyonu."},
            {"exercise": "Leg Extension", "rep_range": "12-20", "rir": 1, "head": "vastus_medialis",
             "why": "Kısalma ucunda izole ekstansör vurgusu."},
        ],
        "key_studies": [
            {"authors": "Pallarés et al.", "year": 2021, "title": "Effects of range of motion on resistance training adaptations: A systematic review and meta-analysis",
             "pmid": "34170576", "journal": "Scand J Med Sci Sports", "link": "https://pubmed.ncbi.nlm.nih.gov/34170576/"},
        ],
        "source_note": "PMID verify_pmid.py ile doğrulanacak.",
        "priority": 8,
    },
    {
        "topic": "biomechanics",
        "question_keywords": "RIR,reps in reserve,set sonu,failure,fail,sona kadar,tükenme,effort,efort,ne kadar zorlamalı",
        "muscle_group": None,
        "focused_exercises": "",
        "direct_answer": (
            "Hipertrofide çoğu seti 1-2 tekrar 'sonda' bırakmak (RIR 1-2) en verimli noktadır; her "
            "sette tam failure, hipertrofiye ekstra katkı yapmadan toparlanma maliyetini artırır."
        ),
        "biomechanics": (
            "Mekanik gerilim ve metabolik yorgunluk, setin son tekrarlarında en yüksek motor ünite "
            "rekrütmanıyla birleşir. Meta-analizler RIR 0 ile RIR 1-3 arasında hipertrofi farkı "
            "bulmazken; ekstra failure RPE'yi ve toparlanma süresini artırır. Bu yüzden setler RIR "
            "1-2 hedeflenir, güvenli hareketlerde son setlerde yalnızca dikkatle yaklaşılır."
        ),
        "exercise_reccs": [],
        "key_studies": [
            {"authors": "Robinson et al.", "year": 2024, "title": "Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure, Strength Gain, and Muscle Hypertrophy: A Series of Meta-Regressions",
             "pmid": "38970765", "journal": "Sports Med", "link": "https://pubmed.ncbi.nlm.nih.gov/38970765/"},
        ],
        "source_note": "PMID verify_pmid.py ile doğrulanacak.",
        "priority": 7,
    },
]
