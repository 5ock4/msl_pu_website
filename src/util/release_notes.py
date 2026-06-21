RELEASE_NOTES = [
    {
        "version": "v1.7.2",
        "entries": [
            "fix(admin): admin může nahrávat a upravovat pozvánku, startovku i výsledky pro libovolné kolo bez ohledu na to, kdo dokument nahrál jako první",
            "fix: po uveřejnění výsledků (Výsledky uveřejněny ✓) nelze výsledkový Excel přepsat — ochrana je vynucena i uvnitř databázové transakce (ochrana před race condition)",
            "fix: neuveřejněné výsledky kola jsou v tabulce výsledků a v tipovačce viditelné pouze pro admina",
            "fix: tlačítka pro úpravu startovky a výsledků se v UI zobrazí až po nahrání prerekvizitních dokumentů (pozvánka resp. startovka), i pro admina",
        ]
    },
    {
        "version": "v1.7.1",
        "entries": [
            "fix: přihlášení magickým odkazem najde existující účet podle e-mailu (dříve vznikal duplicitní účet, pokud měl admin jiné uživatelské jméno než svůj e-mail)",
        ]
    },
    {
        "version": "v1.7.0",
        "entries": [
            "feat: tipovačka — uživatelé tipují prvních 5 týmů v každé kategorii pro každé kolo",
            "feat: tipy se zamykají při odeslání, nedotipované pozice lze doplnit do startu kola",
            "feat: po startu kola je veřejně dostupný přehled všech tipů s vyznačením správných",
            "feat: průběžné pořadí tipovačky za sezónu (body, počet tipů, trefy 1.–5. místa)",
            "feat: filtr sezóny na stránkách tipovačky",
            "feat(admin): správa tipů v sekci 'Tipovačka' s filtrem dle kola, kategorie, pozice a e-mailu uživatele",
        ]
    },
    {
        "version": "v1.6.1",
        "entries": [
            "fix(admin): v sekci 'Parametry MSL' lze zobrazit přehled uživatelských jmen a jejich uživatelů",
        ]
    },
    {
        "version": "v1.6.0",
        "entries": [
            "feat: po prvním přihlášení si uživatel zvolí veřejné uživatelské jméno (3–30 znaků, unikátní)",
            "feat: uživatelské jméno lze kdykoliv změnit přes tlačítko na stránce přihlášení",
            "feat: v hlavičce a na profilu se místo e-mailu zobrazuje uživatelské jméno",
        ]
    },
    {
        "version": "v1.5.2",
        "entries": [
            "fix: výsledkový sloupec na mobilu již není sticky, zobrazí se na konci řádku",
            "fix: ovládací prvky výsledků jsou na mobilu responzivní",
        ]
    },
    {
        "version": "v1.5.1",
        "entries": [
            "fix: admini neviděli výsledky označené jako uveřejněné (results_ready=True) bez nahraného Excelu",
        ]
    },
    {
        "version": "v1.5.0",
        "entries": [
            "feat: nahrávání výsledků (Excel) pro správce kola — stejná práva jako pozvánka/startovka",
            "feat: nahraný Excel uložen ve Wagtail a ke stažení",
            "feat: výsledky viditelné pro adminy ihned po nahrání, pro veřejnost až po zaškrtnutí 'Výsledky uveřejněny'",
            "feat: pořadí povinné — nejdříve pozvánka, pak startovka, teprve pak výsledky",
        ]
    },
    {
        "version": "v1.4.1",
        "entries": [
            "fix(admin): vyhledávání týmu ve výběrovém dialogu v admin sekci",
        ]
    },
    {
        "version": "v1.4.0",
        "entries": [
            "feat: přidány release notes",
            "feat: přidáni sponzoři",
            "fix: odstraněny odkazy na starý web a fórum",
        ]
    },
    {
        "version": "v1.3.0",
        "entries": [
            "feat: pozvánka & startovka upload pro správce kol",
            "feat: přihlášení bez hesla přes magický odkaz (platnost 10 minut)",
            "feat: automatické sdílení aktualit na Facebook při publikaci",
            "fix: načítání .env souboru",
            "fix: práva pro nahrávání startovky a pozvánky",
        ],
    },
    {
        "version": "v1.2.0",
        "entries": [
            "feat: body a finance přepracovány",
            "feat: zlepšení přihlášení, drobné opravy",
        ],
    },
    {
        "version": "v1.1.1",
        "entries": [
            "feat: výsledky — model a stránka",
            "feat: penalizace, drobný refactoring",
            "feat: nové kategorie v selectboxu přihlášky",
            "fix: drobné opravy stylů",
        ],
    },
    {
        "version": "v1.0.0",
        "entries": [
            "feat: MVP — základní funkcionalita webu",
            "feat: aktuality",
            "feat: Bootstrap z npm, vlastní primární barva (SASS)",
        ],
    },
]
