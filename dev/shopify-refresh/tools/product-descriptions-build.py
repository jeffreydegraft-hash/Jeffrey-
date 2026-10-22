# Clean, claim-free, dash-free product descriptions for the Mount of Olives anointing oils.
# Facts (ingredients, scripture references, how to use) are the store's own; only claim wording and formatting change.
import json, os, re
OUT = os.path.dirname(os.path.abspath(__file__))

SHARED = ("<p>At Mount of Olives, our oils go beyond the traditional use of consecrating objects. They are made to anoint both your surroundings and yourself. "
          "Rooted in the anointing traditions of Scripture, every oil carries Polyphenol Alpha (α)™, our complex of polyphenols drawn from biblical botanicals, "
          "so that an oil made for prayer, worship, and blessing also nourishes the skin.</p>")
HOW = ("<h3>How to use</h3>"
       "<ul>"
       "<li>For daily use in times of worship, intercession, consecration, prayer for healing, cleansing, and deliverance.</li>"
       "<li>As a moisturizer, apply after showering and towel-drying, or at any time of day to pulse points such as the wrist.</li>"
       "<li>For a mindful bath, pour a little under warm running water. The oil leaves your skin lightly anointed when you step out.</li>"
       "<li>For external use only.</li>"
       "</ul>")
NAT = "<p>Natural. Paraben-free. Vegan.</p>"

P = {}
P['frankincense-myrrh-anointing-oil'] = dict(
  word='Restore',
  intro="Frankincense and myrrh, two gifts of the Magi, symbolize prayer, worship, and blessing. Frankincense invites a deeper reverence and awareness of God's presence, while myrrh recalls purification and Christ's sacrifice. This blend is made for deepening moments of worship, prayer, and intercession.",
  ingredients=[('Ingredients', 'Olive oil, Boswellia serrata (frankincense), Commiphora myrrha (myrrh)'),
               ('Antioxidants', 'Tyrosol, Hydroxytyrosol, Oleuropein-aglycone dialdehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Tannins, Gallic acid, Quercetin')],
  refs="Genesis 37:25, Genesis 43:11, Leviticus 2:2, Leviticus 2:15-16, Leviticus 6:15, Leviticus 24:7, Numbers 5:15, 1 Chronicles 9:29, Nehemiah 13:5, Nehemiah 13:9, Esther 2:12, Psalm 45:8, Proverbs 7:17, Song of Solomon 1:13, Song of Solomon 3:6, Song of Solomon 4:6, Song of Solomon 4:14, Song of Solomon 5:1, Song of Solomon 5:5, Song of Solomon 5:13, Matthew 2:11, Revelation 18:13")
P['frankincense'] = dict(
  word='Protect',
  intro="Frankincense anointing oil is a sacred symbol of prayer rising before God like incense. It consecrates moments of worship and intercession and brings hearts in line with heaven. Made for creating holy, peaceful spaces during prayer, worship, and consecration.",
  ingredients=[('Ingredients', 'Olive oil, Boswellia serrata (frankincense)'),
               ('Antioxidants', 'Tyrosol, Hydroxytyrosol, Oleuropein-aglycone dialdehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Tannins, Gallic acid, Quercetin')],
  refs="Song of Solomon 4:6, Psalm 141:2, Matthew 2:11")
P['myrrh-anointing-oil-1'] = dict(
  word='Transform',
  intro="Myrrh anointing oil, with its deep history in Scripture, symbolizes purification and consecration. It invites believers to reflect on Christ's sacrifice and the depth of His love. Made for anointing, times of deep intercession, and prayer for restoration.",
  ingredients=[('Ingredients', 'Olive oil, Commiphora myrrha (myrrh), Tyrosol, Hydroxytyrosol, Oleuropein-aglycone dialdehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Tannins, Gallic acid, Quercetin')],
  refs="Esther 2:12, Matthew 2:11, John 19:39")
P['hyssop'] = dict(
  word='Purification & Protection',
  intro="Hyssop has long symbolized spiritual cleansing and renewal in Scripture, from the Passover doorposts to David's prayer, \"Purge me with hyssop, and I shall be clean.\" This oil embodies the purifying power of God's forgiveness. Made for prayers of repentance, spiritual cleansing, and personal renewal through intercession.",
  ingredients=[('Ingredients', 'Olive oil, Hyssopus officinalis (hyssop), Tyrosol, Hydroxytyrosol, Oleuropein-aglycone di-aldehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Ferulic acid, Caffeic acid, Isoquercitrin, Rutin, Quercetin')],
  refs="Exodus 12:22-23, Leviticus 14:4, Leviticus 14:6, Leviticus 14:49, Numbers 19:6, Numbers 19:18, 1 Kings 4:33, Psalm 51:7, John 19:28-30, Hebrews 9:19")
P['spikenard-anointing-oil'] = dict(
  word='Renewal',
  intro="Revered in Scripture, spikenard symbolizes extravagant worship and deep devotion, as when Mary anointed Jesus at Bethany and the fragrance filled the house. Made for consecration, intercession, and worship that draws believers closer to God's presence through surrender.",
  ingredients=[('Ingredients', 'Olive oil, Nardostachys jatamansi (spikenard), Tyrosol, Hydroxytyrosol, Oleuropein-aglycone di-aldehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Gallic acid, Catechin, Chlorogenic acid, Homovanillic acid, Epicatechin, Rutin hydrate, Quercetin-3-rhamnoside')],
  refs="Song of Solomon 1:12, Song of Solomon 4:13-14, Matthew 26:6-13, Mark 14:3-9, John 12:1-8")
P['latter-rain-anointing-oil'] = dict(
  word='Revitalize',
  intro="Symbolizing the latter rain, the outpouring of the Holy Spirit promised through the prophets, this oil is made for times of spiritual revival and renewal, and for remembering God's promise of blessing and restoration. Made for prayer meetings, revival services, and personal renewal.",
  ingredients=[('Ingredients', 'Olive oil, Luteolin, Resins, Tyrosol, Hydroxytyrosol, Oleuropein-aglycone dialdehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Apigenin, Pinoresinol, Squalene, Ellagitannins')],
  refs="Deuteronomy 11:14, Job 29:23, Proverbs 16:15, Jeremiah 3:3, Jeremiah 5:24, Hosea 6:3, Joel 2:23, Zechariah 10:1, James 5:7")
P['lily-of-the-valley'] = dict(
  word='Illuminate',
  intro="Symbolizing purity and peace, Lily of the Valley anointing oil recalls the lily of the valleys of the Song of Solomon and the lilies of the field that Jesus pointed to. Made for personal devotion, intercession, and a sense of sacred peace in moments of prayer and consecration.",
  ingredients=[('Ingredients', 'Olive oil, Luteolin, Resins, Tyrosol, Hydroxytyrosol, Oleuropein-aglycone di-aldehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone dialdehyde, Apigenin, Pinoresinol, Squalene, Ellagitannins')],
  refs="Song of Solomon 2:1-2, Song of Solomon 6:2, Hosea 14:5, Matthew 6:28-29, Luke 12:27")
P['pomegranate-anointing-oil'] = dict(
  word='Eternal',
  intro="Pomegranate, a symbol of fruitfulness and abundance, was woven into the hem of the high priest's robe and carved into the pillars of the temple. This oil reflects God's blessings and His covenant with His people. Made for consecration, prayer, and worship that gives thanks for God's abundant blessing.",
  ingredients=[('Ingredients', 'Olive oil, Punica granatum (pomegranate), Tyrosol, Hydroxytyrosol, Oleuropein-aglycone di-aldehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Gallic acid, Ellagic acid, Punicalagin A and B, Punicalin A and B')],
  refs="Exodus 28:34, Exodus 39:24, Numbers 13:23, Numbers 20:5, Deuteronomy 8:8, 1 Samuel 14:2, 1 Kings 7:20, 1 Kings 7:42, 2 Kings 25:17, 2 Chronicles 3:16, 2 Chronicles 4:13, Song of Solomon 4:3, Song of Solomon 4:13, Song of Solomon 6:7, Song of Solomon 6:11, Song of Solomon 7:12, Song of Solomon 8:2, Jeremiah 52:22-23, Joel 1:12, Haggai 2:19")
P['rose-of-sharon'] = dict(
  word='Radiance',
  intro="The Rose of Sharon symbolizes Christ's beauty, love, and purity, \"I am the rose of Sharon, and the lily of the valleys.\" This oil is made for moments of worship, prayer, and personal devotion, for consecration and intercession, and for a sense of spiritual renewal and peace.",
  ingredients=[('Ingredients', 'Olive oil, Cistus ladaniferus (rose of Sharon)'),
               ('Antioxidants', 'Tyrosol, Hydroxytyrosol, Oleuropein-aglycone, Ligstroside-aglycone, Luteolin, Apigenin, Pinoresinol, Squalane, Ellagitannins, Tannins, Gallic acid, Quercetin')],
  refs="Song of Solomon 2:1, Isaiah 65:10")
P['gethsemane-anointing-oil-unscented'] = dict(
  word='Unscented',
  intro="This pure, unscented oil reflects the simplicity of Christ's prayer in the garden of Gethsemane, among the olive trees. It is a fragrance-free option for intercession, anointing, and personal reflection. Made for moments of prayer and consecration without any added fragrance.",
  ingredients=[('Ingredients', 'Olive oil, Squalane, Tyrosol, Hydroxytyrosol, Oleuropein-aglycone dialdehyde, Oleuropein-aglycone mono-aldehyde, Ligstroside-aglycone di-aldehyde, Luteolin, Apigenin, Pinoresinol, Squalene')],
  refs="Leviticus 8:12, 1 Samuel 16:13, Psalm 23:5, Matthew 26:36, James 5:14-16")

def product_html(h):
    d = P[h]
    s = f"<p><strong>{d['word'].upper()}</strong></p>"
    s += f"<p>{d['intro']}</p>"
    s += SHARED
    s += "<h3>All natural formulation</h3>" + NAT
    for label, val in d['ingredients']:
        s += f"<p><strong>{label}:</strong> {val}</p>"
    s += "<p>All ingredients are naturally derived from biblical botanicals.</p>"
    s += HOW
    s += "<h3>Scripture references</h3>" + f"<p>{d['refs']}</p>"
    return s

SQUALANE = (
  "<p><strong>HYDRATE</strong></p>"
  "<p>From the olive, the tree Scripture names more than any other: the oil that lit the tabernacle (Exodus 27:20) and anointed kings (1 Samuel 16:13). "
  "Our 100% olive squalane is the base of every anointing oil we make, offered here on its own.</p>"
  "<p>Squalane is a light, stable oil derived from the olive, and it is vegan and sustainably sourced. It absorbs quickly without feeling greasy, "
  "moisturizes, and helps the skin hold on to hydration, leaving it soft and supple. It is non-comedogenic and suited to all skin types. "
  "On hair it adds shine and smooths flyaways.</p>"
  "<h3>All natural formulation</h3>"
  "<p>Natural. Paraben-free. Vegan.</p>"
  "<p><strong>Ingredients:</strong> 100% olive-derived squalane</p>"
  "<h3>How to use</h3>"
  "<ul>"
  "<li>Face: warm a few drops between your hands and press gently into the face, neck, and décolleté.</li>"
  "<li>Body: apply a few drops after showering, especially to arms, legs, and knees.</li>"
  "<li>Hair: smooth a small amount through dry or damp hair to add shine and tame flyaways.</li>"
  "<li>For external use only.</li>"
  "</ul>"
  "<h3>Scripture references</h3>"
  "<p>Exodus 27:20, 1 Samuel 16:13, Psalm 23:5, Matthew 26:36</p>")

COLLECTIONS = {
  'rose-of-sharon': "<p>Discover the Rose of Sharon, the flower of the Song of Solomon: \"I am the rose of Sharon, and the lily of the valleys\" (Song of Solomon 2:1). Our Rose of Sharon anointing oil is crafted from Cistus ladaniferus in a base of olive oil with Polyphenol Alpha (α)™, our complex of polyphenols from biblical botanicals. Made for worship, prayer, personal devotion, consecration, and intercession, and it nourishes the skin.</p>",
  'pomegranate': "<p>Discover the Pomegranate, one of the seven species of the Promised Land (Deuteronomy 8:8), woven into the hem of the high priest's robe and carved into the pillars of the temple. Our Pomegranate anointing oil is crafted from Punica granatum in a base of olive oil with Polyphenol Alpha (α)™, our complex of polyphenols from biblical botanicals. Made for consecration, prayer, and worship that gives thanks for God's abundant blessing, and it nourishes the skin.</p>",
  'serums': "<p>Our 100% olive squalane, the base of every anointing oil we make, offered on its own. From the olive, the tree that lit the tabernacle and anointed kings, it is light, vegan, and sustainably sourced. It absorbs quickly, moisturizes, and leaves the skin soft and supple.</p>",
}

out = {'products': {h: product_html(h) for h in P}, 'squalane': SQUALANE, 'collections': COLLECTIONS}
allhtml = json.dumps(out, ensure_ascii=False)
assert '—' not in allhtml and '–' not in allhtml, 'dash found'
bad = re.compile(r'anti-?inflammator|therapeutic|clinical|penetrat|superior|synergis|protective|restorativ|efficac|effective|scientific|proven|\bcures?\b|\btreats?\b|medicinal|wellness|anti-?aging|collagen|regenerat|repair|elastic|wrinkle|acne|eczema|bioidentical|surpass|heat protection|breakage|antimicrobial|antiseptic|antibacterial|high-performance|skin health', re.I)
for h, html in {**out['products'], 'squalane': SQUALANE, **COLLECTIONS}.items():
    m = bad.search(html)
    assert not m, (h, m.group(0))
json.dump(out, open(OUT + '/descriptions.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for h, html in out['products'].items(): open(f'{OUT}/product-{h}.html', 'w', encoding='utf-8').write(html + '\n')
open(f'{OUT}/product-100-squalane.html', 'w', encoding='utf-8').write(SQUALANE + '\n')
for h, html in COLLECTIONS.items(): open(f'{OUT}/collection-{h}.html', 'w', encoding='utf-8').write(html + '\n')
print('ok', len(out['products']), 'products + squalane +', len(COLLECTIONS), 'collections')
