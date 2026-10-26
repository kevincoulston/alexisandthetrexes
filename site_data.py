"""Content for alexisandthetrexes.com. build.py turns this into dist/.

Book facts were read from the Amazon listings on Oct 26, 2026 (see book-isbns.csv).
Kevin's rules: Snap is the orange boy T-Rex, Daisy is the blue girl T-Rex. Never credit or mention anyone else as a creator.
"""

SITE = "https://alexisandthetrexes.com"
GA_ID = "G-FEWWZYTBCV"  # GA4 measurement ID, loaded on first interaction or after 4 s (Kevin, Oct 26 2026)
SERIES_URL = "https://www.amazon.com/dp/B08YWDNZ4D"
AUTHOR_STORE = "https://www.amazon.com/stores/author/B00JC406ZE"

BOOKS = [
    {
        "slug": "count-to-ten",
        "num": 1,
        "title": "Count to Ten",
        "full": "Alexis and the T-Rexes: Count to Ten",
        "asin": "1660378885",
        "isbn13": "9781660378883",
        "isbn13_h": "978-1660378883",
        "isbn10": "1660378885",
        "pages": 24,
        "date": "2020-01-15",
        "date_text": "January 15, 2020",
        "stars": "5.0",
        "ratings": 14,
        "cover": "cover-count-to-ten.webp",
        "cover_alt": "Cover of Alexis and the T-Rexes: Count to Ten, with Alexis, Snap and Daisy in front of a yellow house",
        "blurb": "In their very first book, five-year-old Alexis and her baby dinosaur friends spend an exciting day together while learning to count to ten.",
        "theme": "Counting 1 to 10",
        "learn": [
            "Counting from one to ten, one number at a time",
            "Matching numbers to things you can see and point at",
            "Meeting Alexis, Snap and Daisy for the very first time",
        ],
        "tip": "Point to each dinosaur as you read and let your child say the number out loud. Then count something real together: toys, snacks or stairs.",
    },
    {
        "slug": "birthday-surprise",
        "num": 2,
        "title": "Birthday Surprise",
        "full": "Alexis and the T-Rexes: Birthday Surprise",
        "asin": "B084DP5DGW",
        "isbn13": "9798600000476",
        "isbn13_h": "979-8600000476",
        "isbn10": "",
        "pages": 30,
        "date": "2020-02-08",
        "date_text": "February 8, 2020",
        "stars": "5.0",
        "ratings": 9,
        "cover": "cover-birthday-surprise.webp",
        "cover_alt": "Cover of Alexis and the T-Rexes: Birthday Surprise, with Alexis, a carrot birthday cake and the T-Rexes under balloons",
        "blurb": "While celebrating a birthday, Alexis and the T-Rexes learn that sometimes the best gift is something you make yourself.",
        "theme": "Handmade gifts",
        "learn": [
            "Why a gift you make yourself can be the best gift of all",
            "Thinking about what would make someone else happy",
            "Birthday fun with Alexis, Snap and Daisy",
        ],
        "tip": "After reading, make a gift together for someone you love: a drawing, a card or something built from blocks.",
    },
    {
        "slug": "hide-and-seek",
        "num": 3,
        "title": "Hide and Seek",
        "full": "Alexis and the T-Rexes: Hide and Seek",
        "asin": "B0884K4ZRH",
        "isbn13": "9798612822141",
        "isbn13_h": "979-8612822141",
        "isbn10": "",
        "pages": 30,
        "date": "2020-05-06",
        "date_text": "May 6, 2020",
        "stars": "5.0",
        "ratings": 3,
        "cover": "cover-hide-and-seek.webp",
        "cover_alt": "Cover of Alexis and the T-Rexes: Hide and Seek, with Alexis, Abigail and three baby T-Rexes around a big tree",
        "blurb": "Alexis' best friend Abigail comes over for a playdate, and together they teach their baby dinosaur friends how to play hide-and-seek.",
        "theme": "Playing together",
        "learn": [
            "How to play hide-and-seek, step by step",
            "Playing together and taking turns with a friend",
            "Meeting Alexis' best friend, Abigail",
        ],
        "tip": "Hide a stuffed dinosaur somewhere in the house and take turns being the seeker, just like Alexis and Abigail.",
    },
]

GANG = [
    {"name": "Alexis", "img": "alexis-wave.webp", "alt": "Alexis waving hello, in her green cupcake apron",
     "short": "Five years old, big imagination, and best friend to two baby T-Rexes.",
     "long": "Alexis is five years old and has two very special friends: baby T-Rexes named Snap and Daisy. Together they count, celebrate birthdays and play games, and Alexis is always ready to show them how things work."},
    {"name": "Snap", "img": "snap.webp", "alt": "Snap, the orange baby T-Rex, smiling with his arms out",
     "short": "Alexis' orange baby T-Rex. He's a boy, and he's always ready to play.",
     "long": "Snap is the orange baby T-Rex. He's a boy with a big toothy grin, and he's always up for whatever Alexis has planned."},
    {"name": "Daisy", "img": "daisy.webp", "alt": "Daisy, the blue baby T-Rex with a red bow, giggling",
     "short": "Alexis' blue baby T-Rex. She's a girl, and she never goes anywhere without her red bow.",
     "long": "Daisy is the blue baby T-Rex. She's a girl with a red bow and a big smile, and she loves joining in on every game."},
    {"name": "Abigail", "img": "abigail.webp", "alt": "Abigail peeking around a tree, with her pink baby T-Rex", "round": True,
     "short": "Alexis' best friend, who comes over to play in Hide and Seek.",
     "long": "Abigail is Alexis' best friend. She comes over for a playdate in Hide and Seek, along with a pink baby T-Rex of her own."},
]

FREE_PAGES = [
    {"title": "How to draw a Brachiosaurus", "kind": "A six-step drawing page", "img": "page-brachiosaurus.webp",
     "book": "How to Draw: Cartoon Dinosaurs", "book_url": "https://www.amazon.com/dp/B0BW2SDFT6",
     "url": "https://firstartbooks.com/how-to-draw-a-brachiosaurus/"},
    {"title": "Draw a Plesiosaur by grid", "kind": "A square-by-square grid drawing page", "img": "page-plesiosaur.webp",
     "book": "Draw by Grid: Cartoon Dinosaurs", "book_url": "https://www.amazon.com/dp/B0CFZR7QL2",
     "url": "https://firstartbooks.com/how-to-draw-a-plesiosaur/"},
    {"title": "Trace a Parasaurolophus", "kind": "A trace-then-color page", "img": "page-parasaurolophus.webp",
     "book": "Trace Then Color: Cartoon Dinosaurs", "book_url": "https://www.amazon.com/dp/B0BW2RY5ZM",
     "url": "https://firstartbooks.com/parasaurolophus-coloring-page/"},
]

DINO_BOOKS = [
    {"title": "How to Draw: Cartoon Dinosaurs", "img": "cover-htd-dinos.webp", "url": "https://www.amazon.com/dp/B0BW2SDFT6",
     "fab": "https://firstartbooks.com/product/how-to-draw-cartoon-dinosaurs/", "what": "Step-by-step drawing lessons"},
    {"title": "Trace Then Color: Cartoon Dinosaurs", "img": "cover-ttc-dinos.webp", "url": "https://www.amazon.com/dp/B0BW2RY5ZM",
     "fab": "https://firstartbooks.com/product/trace-then-color-cartoon-dinosaurs/", "what": "Trace the lines, then color"},
    {"title": "Draw by Grid: Cartoon Dinosaurs", "img": "cover-dbg-dinos.webp", "url": "https://www.amazon.com/dp/B0CFZR7QL2",
     "fab": "https://firstartbooks.com/product/draw-by-grid-cartoon-dinosaurs/", "what": "Copy the picture square by square"},
]
