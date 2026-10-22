# Builds templates/page.our-science.json for the Prestige work copy and the matching page body (no em dashes anywhere).
import json, re, sys, html
S = '.'
IMG = 'shopify://shop_images/'
P = {  # products
  'olive': '/products/100-squalane', 'frank': '/products/frankincense', 'myrrh': '/products/myrrh-anointing-oil-1',
  'pom': '/products/pomegranate-anointing-oil', 'hyssop': '/products/hyssop', 'spike': '/products/spikenard-anointing-oil',
  'rose': '/products/rose-of-sharon', 'lily': '/products/lily-of-the-valley', 'fm': '/products/frankincense-myrrh-anointing-oil',
}
PA = 'Polyphenol Alpha (α)™'

hero_text = (
  '<p><em>Where the wisdom of Scripture meets careful craft.</em></p>'
  '<p>Anointing with oil runs through the whole of Scripture: the holy anointing oil of Exodus 30, the horn of oil that anointed David, the oil of gladness of the Psalms, the alabaster jar broken at Bethany. '
  'Every Mount of Olives oil begins with the plants, resins, and extracts those pages name, revered for millennia: '
  '<strong>frankincense, myrrh, spikenard, hyssop, pomegranate, rose of Sharon, and lily of the valley</strong>.</p>'
  '<p>We prepare them with care in a base of olive squalane, so that an oil made for prayer, worship, and blessing also nourishes the skin. This page explains what is in every bottle.</p>'
)

standards = [
  ('picto-leaf', 'Naturally derived actives', 'Every active compound comes from a plant, resin, fruit, or seed. We do not synthesize our actives in a lab.'),
  ('picto-not-allowed', 'No parabens, no sulfates', 'Free from parabens, phthalates, sulfates, and synthetic fragrances. We exclude ingredients that do not align with our values.'),
  ('picto-shield', 'Non-comedogenic', 'Formulated to nourish the skin without clogging pores.'),
  ('picto-love', 'Cruelty-free', 'We honor all of God’s creation and never test on animals.'),
  ('picto-recycle', 'Transparent and sustainable', 'Recyclable and biodegradable packaging. Every compound published with its botanical origin.'),
]

squalane_tab = (
  '<p>We formulate our anointing oils in a base of <strong>100% olive-derived squalane</strong>, a naturally occurring lipid closely related to the squalene found in human skin.</p>'
  '<p>Squalane is a light, stable oil. It spreads easily, carries the botanical extracts with it, and leaves the skin feeling hydrated rather than greasy. '
  'We use no chemical solvents or artificial emulsifiers.</p>'
  '<p>Squalane comes from the fruit of the olive tree, a tree that appears in Scripture more than any other: the oil that lit the lamps of the tabernacle (Exodus 27:20), the base of the holy anointing oil (Exodus 30:22-25), and the oil with which Samuel anointed David (1 Samuel 16:13). Our name comes from the same tree: the Mount of Olives, where Jesus prayed in the garden of Gethsemane.</p>'
  f'<p><a href="{P["olive"]}">Shop 100% Squalane</a></p>'
)
pa_tab = (
  f'<p>Central to every Mount of Olives formulation is <strong>{PA}</strong>, our proprietary antioxidant-rich polyphenol complex, derived entirely from natural botanical sources. '
  'It brings together several families of plant polyphenols: flavonoids, phenolic acids, stilbenes, and lignans.</p>'
  f'<p>{PA} is not a single ingredient. It is a <strong>blend of many compounds</strong> working together, much the way Scripture describes the body: <em>“many parts, but one body”</em> (1 Corinthians 12:20).</p>'
  '<p><a href="#ingredients">Read the full ingredient glossary</a></p>'
)
botanicals_tab = (
  '<p>Every active compound in our formulations is a <strong>natural derivative</strong> of a plant, resin, fruit, or seed with deep biblical significance. We do not synthesize our actives in a laboratory. We extract, purify, and concentrate them from the same botanical sources that God placed in creation.</p>'
  '<ul>'
  f'<li><strong>Boswellic acids</strong> from <em>Boswellia serrata</em> (<a href="{P["frank"]}">frankincense</a>), the resin of the Magi</li>'
  f'<li><strong>Terpenoids and sesquiterpenes</strong> from <em>Commiphora myrrha</em> (<a href="{P["myrrh"]}">myrrh</a>), the resin of purification</li>'
  f'<li><strong>Ellagitannins and punicalagins</strong> from <em>Punica granatum</em> (<a href="{P["pom"]}">pomegranate</a>), one of the seven blessed fruits of the Promised Land</li>'
  '<li><strong>Hydroxytyrosol and oleuropein</strong> from <em>Olea europaea</em> (olive), the tree of peace</li>'
  f'<li><strong>Apigenin and flavonoids</strong> from <em>Hyssopus officinalis</em> (<a href="{P["hyssop"]}">hyssop</a>), the herb of purification (Psalm 51:7)</li>'
  f'<li><strong>Jatamansone and sesquiterpenes</strong> from <em>Nardostachys jatamansi</em> (<a href="{P["spike"]}">spikenard</a>), the precious oil of Mary of Bethany</li>'
  f'<li><strong>Labdanum and polyphenols</strong> from <em>Cistus ladaniferus</em> (<a href="{P["rose"]}">rose of Sharon</a>), the flower of Song of Solomon</li>'
  '</ul>'
  '<p>These are not synthetic analogs or lab-created substitutes. They are the <strong>natural constituents</strong> of the very plants Scripture names: extracted, concentrated, and blended into our oils.</p>'
)
standards_tab = (
  '<p>We believe that what we place on our bodies, temples of the Holy Spirit, deserves the highest standards of purity and care. Our commitment:</p>'
  '<ul>'
  '<li><strong>100% naturally derived active ingredients.</strong> Every active compound originates from a botanical source.</li>'
  '<li><strong>Free from parabens, phthalates, sulfates, and synthetic fragrances.</strong> We exclude ingredients that do not align with our values.</li>'
  '<li><strong>Non-comedogenic formulation.</strong> Made to nourish the skin without clogging pores.</li>'
  '<li><strong>Cruelty-free.</strong> We honor all of God’s creation and never test on animals.</li>'
  '<li><strong>Sustainable, eco-conscious packaging.</strong> Recyclable and biodegradable materials, as part of our stewardship of the earth.</li>'
  '<li><strong>Full ingredient transparency.</strong> We publish every compound and its botanical origin, because we believe informed customers are empowered customers.</li>'
  '</ul>'
)

cards = [  # (image file, title, latin line, text, link text, link)
  ('olive-trees-gethsemane-mount-of-olives.jpg', 'Olive', 'Olea europaea', 'The tree of peace, and the tree of Gethsemane. Its oil anointed kings and priests. Our squalane base and its polyphenols, hydroxytyrosol and oleuropein, come from its fruit.', 'Shop 100% Squalane', P['olive']),
  ('frankincense-bible-sacred-resin-anointing-spiritual-healing.jpg', 'Frankincense', 'Boswellia serrata', 'A symbol of prayer rising before God like incense, and a gift of the Magi (Matthew 2:11). Its resin gives us boswellic acids.', 'Shop Frankincense', P['frank']),
  ('myrrh-bible-ancient-oil-healing-anointing.jpg', 'Myrrh', 'Commiphora myrrha', 'A symbol of purification and of Christ\u2019s sacrifice, and a gift of the Magi. Its resin gives us terpenoids and sesquiterpenes.', 'Shop Myrrh', P['myrrh']),
  ('a-beautiful-ripe-pomegranate-split-open-revealing-ruby-red-seeds-on-a-rustic-wooden-surface-with-a-small-glass-bottle-of-golden-anointing-oil-beside-it-warm-golden-light-biblical-abun.png', 'Pomegranate', 'Punica granatum', 'A symbol of fruitfulness and abundance, one of the seven blessed fruits of the Promised Land (Deuteronomy 8:8). Its fruit and seed give us ellagitannins and punicalagins.', 'Shop Pomegranate', P['pom']),
  ('hyssop-bible-sacred-herb-purification-cleansing.jpg', 'Hyssop', 'Hyssopus officinalis', 'The herb of purification: \u201cPurge me with hyssop, and I shall be clean\u201d (Psalm 51:7). It gives us apigenin and other flavonoids.', 'Shop Hyssop', P['hyssop']),
  ('spikenard-bible-precious-oil-mary-anointed-jesus.jpg', 'Spikenard', 'Nardostachys jatamansi', 'The precious oil Mary of Bethany poured out in extravagant worship (John 12:3). Its root gives us jatamansone and sesquiterpenes.', 'Shop Spikenard', P['spike']),
  ('rose-of-sharon-biblical-flower-healing.jpg', 'Rose of Sharon', 'Cistus ladaniferus', '\u201cI am the rose of Sharon\u201d (Song of Solomon 2:1). The labdanum shrub of the Mediterranean, rich in polyphenols.', 'Shop Rose of Sharon', P['rose']),
  ('beautiful-lily-of-the-valley-flowers-with-delicate-white-bell-shaped-blossoms-on-green-stems-soft-golden-light-a-small-glass-bottle-of-anointing-oil-nearby-warm-spiritual-atmosphere-b.png', 'Lily of the Valley', 'Song of Solomon 2:1', 'A symbol of purity and peace: \u201cthe lily of the valleys\u201d of Song of Solomon 2:1, one of the plants every product in our collection begins with.', 'Shop Lily of the Valley', P['lily']),
]

timeline = [  # (image, label, subheading, title, content, link text, link url)
  ('ornate-ancient-vessels-of-gold-frankincense-resin-and-myrrh-presented-as-gifts-on-rich-fabric-glowing-star-of-bethlehem-in-the-night-sky-through-an-open-window-warm-golden-candlelight.png', '01', 'Rooted in Scripture', 'The plants come first',
   '<p>The plants, resins, and extracts that Scripture names, revered for millennia, are where every product begins.</p>', '', ''),
  ('ancient-sacred-anointing-oil-ingredients-from-exodus-30-arranged-on-a-stone-altar-myrrh-resin-cinnamon-sticks-cassia-bark-and-olive-oil-in-a-golden-vessel-warm-candlelight-holy-tabern.png', '02', 'Extracted, not synthesized', 'The plant’s own compounds',
   '<p>The actives are extracted, purified, and concentrated from the plants themselves, the same botanical sources God placed in creation, not made in a laboratory.</p>', '', ''),
  ('squalane1oz.jpg', '03', 'Carried by olive squalane', 'The oil of Scripture',
   '<p>Each extract is carried in 100% olive-derived squalane, from the tree that lit the tabernacle and anointed kings. A light, stable oil, with no chemical solvents or artificial emulsifiers.</p>', 'Shop 100% Squalane', P['olive']),
  ('praying-with-frankincense-myrrh.jpg', '04', 'Made for anointing', 'For prayer, worship, and blessing',
   '<p>An oil for the moments Scripture describes: consecration, intercession, worship, and prayer for healing. It honors that tradition and nourishes the skin.</p>', 'Shop the collection', 'shopify://collections/all'),
]

glossary = {
  ('From the olive', 'picto-tree'): [
    ('Hydroxytyrosol', 'A polyphenol found mainly in olives and olive oil. An antioxidant.'),
    ('Tyrosol', 'A phenolic antioxidant found in olives, olive oil, and wine.'),
    ('Oleuropein-aglycone dialdehyde', 'A secoiridoid polyphenol from olives. An antioxidant.'),
    ('Oleuropein-aglycone mono-aldehyde', 'A closely related olive secoiridoid, also an antioxidant, that rounds out the olive polyphenols in our formulations.'),
    ('Ligstroside-aglycone di-aldehyde', 'A secoiridoid compound found in olives and extra virgin olive oil. An antioxidant.'),
    ('Pinoresinol', 'A lignan found in olives, olive oil, and sesame seeds. An antioxidant.'),
    ('Olive oil (Olea europaea)', 'Cold-pressed from the fruit of the olive tree, the most frequently referenced tree in all of Scripture. Rich in oleic acid, squalene, hydroxytyrosol, and tocopherols. A nourishing emollient and the natural source of the compounds at the heart of our ' + PA + ' complex.'),
    ('Squalane (olive-derived)', 'A fully saturated, stable hydrocarbon made by hydrogenating squalene from <em>Olea europaea</em> (olive). Closely related to the squalene naturally present in human skin, it is a light emollient that leaves the skin feeling hydrated, not greasy. Non-comedogenic, odorless, and oxidatively stable: the carrier for our ' + PA + ' complex.'),
  ],
  ('Frankincense and myrrh', 'picto-gift'): [
    ('Boswellia serrata (frankincense)', 'A resin from the bark of the <em>Boswellia serrata</em> tree, native to India and the Middle East. It contains boswellic acids (AKBA and KBA). One of the three gifts the Magi presented to the Christ child (Matthew 2:11), and a cornerstone ingredient in ancient anointing formulations.'),
    ('Commiphora myrrha (myrrh)', 'An oleoresin harvested from the <em>Commiphora myrrha</em> tree of the Arabian Peninsula and northeastern Africa. It contains terpenoids (curzerene, furanoeudesma-1,3-diene), sesquiterpenes, and flavonoids. A gift of the Magi and a biblical symbol of purification, consecration, and healing.'),
    ('Botanical resins', 'Natural oleoresins from frankincense, myrrh, and labdanum: complex mixtures of terpenes, sesquiterpenes, and phenolic acids, used in traditional formulations for millennia.'),
  ],
  ('Herbs and flowers', 'picto-leaf'): [
    ('Hyssopus officinalis (hyssop)', 'The biblical herb of purification named in Psalm 51:7: <em>“Purge me with hyssop, and I shall be clean.”</em> It contains apigenin, rosmarinic acid, and essential oil terpenes.'),
    ('Nardostachys jatamansi (spikenard)', 'The precious aromatic rhizome Mary of Bethany used to anoint Jesus before his burial (John 12:3). It contains jatamansone, nardosinone, and sesquiterpenes. One of the rarest and most valued botanicals in our collection.'),
    ('Cistus ladaniferus (rose of Sharon)', 'The labdanum-producing Mediterranean shrub referenced as the rose of Sharon in Song of Solomon 2:1. Rich in polyphenols.'),
  ],
  ('Pomegranate', 'picto-star'): [
    ('Punica granatum (pomegranate)', 'One of the seven species blessed in the Torah (Deuteronomy 8:8). The fruit and seed contain ellagitannins, punicalagins A and B, punicalin, gallic acid, and ellagic acid, all polyphenols.'),
    ('Ellagitannins', 'Tannins found in pomegranates, raspberries, and walnuts. Antioxidant polyphenols.'),
  ],
  ('The wider polyphenol family', 'picto-shield'): [
    ('Apigenin', 'A flavonoid naturally present in parsley (<em>Petroselinum crispum</em>), chamomile (<em>Matricaria chamomilla</em>), celery (<em>Apium graveolens</em>), and hyssop (<em>Hyssopus officinalis</em>). An antioxidant.'),
    ('Caffeic acid', 'A hydroxycinnamic acid found in coffee, wine, and many plants. An antioxidant.'),
    ('Catechin', 'A flavan-3-ol polyphenol abundant in tea (<em>Camellia sinensis</em>) and many fruits. An antioxidant.'),
    ('Chlorogenic acid', 'A phenolic compound found in coffee and stone fruits. An antioxidant.'),
    ('Epicatechin', 'A flavanol found in tea and cocoa. An antioxidant.'),
    ('Ferulic acid', 'A phenolic compound from rice bran, wheat, and oats. An antioxidant. A key component of our ' + PA + ' complex.'),
    ('Gallic acid', 'A trihydroxybenzoic acid found in grapes, tea leaves, and oak bark. An antioxidant.'),
    ('Homovanillic acid', 'A phenolic compound found in vanilla beans and select botanical sources. An antioxidant.'),
    ('Isoquercitrin', 'A quercetin glycoside found in apples, onions, and various plants. An antioxidant.'),
    ('Luteolin', 'A flavone found in celery, parsley, and thyme. An antioxidant.'),
    ('Quercetin', 'One of the most abundant dietary flavonoids, found in apples, onions, berries, and tea. An antioxidant.'),
    ('Quercitrin (quercetin-3-rhamnoside)', 'A quercetin glycoside found in citrus fruits and berries. An antioxidant.'),
    ('Rutin', 'A flavonoid glycoside found in buckwheat, apples, and citrus. An antioxidant.'),
  ],
}

sections = {}
order = []
def add(key, sec):
  sections[key] = sec; order.append(key)

add('hero', {'type': 'rich-text', 'blocks': {
  'sub': {'type': 'subheading', 'settings': {'text': 'Our science'}},
  'head': {'type': 'heading', 'settings': {'text': 'The science of sacred botanicals', 'heading_tag': 'h1'}},
  'text': {'type': 'richtext', 'settings': {'content': hero_text}},
  'shop': {'type': 'button', 'settings': {'style': 'solid', 'text': 'Shop the oils', 'url': 'shopify://collections/all'}},
  'glossary': {'type': 'liquid', 'settings': {'liquid': '<a class="link" href="#ingredients">See every ingredient</a>'}},
}, 'block_order': ['sub', 'head', 'text', 'shop', 'glossary'],
  'settings': {'color_scheme': 'scheme-1', 'separate_section_with_border': False, 'content_width': 'md', 'text_position': 'center', 'remove_vertical_spacing': False}})

blocks = {}; bo = []
for i, (icon, title, text) in enumerate(standards, 1):
  blocks[f'std-{i}'] = {'type': 'item', 'settings': {'icon': icon, 'icon_width': 32, 'mobile_icon_width': 28, 'title': title, 'content': f'<p>{text}</p>'}}; bo.append(f'std-{i}')
add('standards', {'type': 'text-with-icons', 'blocks': blocks, 'block_order': bo,
  'settings': {'color_scheme': 'scheme-5', 'separate_section_with_border': False, 'stack_on_mobile': False, 'text_alignment': 'center'}})

blocks = {}; bo = []
for i, (img, label, sub, title, content, lt, lu) in enumerate(timeline, 1):
  s = {'image': IMG + img, 'label': label, 'subheading': sub, 'title': title, 'content': content, 'link_text': lt, 'link_style': 'link', 'mobile_text_color': '#ffffff'}
  if lu: s['link_url'] = lu
  blocks[f'step-{i}'] = {'type': 'item', 'settings': s}; bo.append(f'step-{i}')
add('how', {'type': 'timeline', 'blocks': blocks, 'block_order': bo,
  'settings': {'color_scheme': 'scheme-1', 'item_color_scheme': 'scheme-2', 'separate_section_with_border': False}})

add('inside', {'type': 'tabs', 'blocks': {
  'squalane': {'type': 'tab', 'settings': {'title': 'Olive squalane base', 'content': squalane_tab, 'open_on_mobile': True}},
  'complex': {'type': 'tab', 'settings': {'title': 'The polyphenol complex', 'content': pa_tab, 'open_on_mobile': False}},
  'botanicals': {'type': 'tab', 'settings': {'title': 'The botanicals', 'content': botanicals_tab, 'open_on_mobile': False}},
  'standards': {'type': 'tab', 'settings': {'title': 'Our standards', 'content': standards_tab, 'open_on_mobile': False}},
}, 'block_order': ['squalane', 'complex', 'botanicals', 'standards'],
  'settings': {'color_scheme': 'scheme-2', 'separate_section_with_border': False, 'subheading': 'Our formulation', 'title': 'What is in every bottle', 'text_alignment': 'center'}})

blocks = {}; bo = []
for i, (img, title, latin, text, lt, lu) in enumerate(cards, 1):
  blocks[f'plant-{i}'] = {'type': 'image_with_text', 'settings': {'image': IMG + img, 'title': title, 'heading_tag': 'h3', 'content': f'<p><em>{latin}</em></p><p>{text}</p>', 'link_url': lu, 'link_text': lt}}; bo.append(f'plant-{i}')
add('botanicals', {'type': 'multi-column', 'blocks': blocks, 'block_order': bo,
  'settings': {'color_scheme': 'scheme-1', 'separate_section_with_border': False, 'columns_per_row': 4, 'stack_on_mobile': False, 'overlap_image': False,
               'content_alignment': 'start', 'text_alignment': 'start', 'spacing': 'md', 'subheading': 'From creation', 'title': 'The plants Scripture names',
               'content': '<p>Every product in our collection begins with these plants, each with its own place in Scripture. Tap a botanical to shop its oil.</p>'}})

look1 = [('rose-of-sharon', 17), ('latter-rain-anointing-oil', 41), ('hyssop', 65), ('spikenard-anointing-oil', 88)]
look2 = [('lily-of-the-valley', 11), ('frankincense-myrrh-anointing-oil', 37), ('pomegranate-anointing-oil', 60), ('gethsemane-anointing-oil-unscented', 84)]
def look(img, prods):
  s = {'image': IMG + img, 'hot_spots_background': '#c4a265'}
  for i, (h, x) in enumerate(prods, 1):
    s[f'product_{i}'] = h; s[f'product_{i}_horizontal_position'] = x; s[f'product_{i}_vertical_position'] = 33
  return {'type': 'look', 'settings': s}
add('look', {'type': 'shop-the-look', 'blocks': {'look-1': look('mo-science-look-1.jpg', look1), 'look-2': look('mo-science-look-2.jpg', look2)}, 'block_order': ['look-1', 'look-2'],
  'settings': {'color_scheme': 'scheme-2', 'separate_section_with_border': False, 'subheading': 'The collection', 'title': 'Tap a bottle',
               'content': '<p>Every oil is built on the same olive squalane base. Tap a bottle to see the oil and add it to your cart.</p>', 'popover_title': 'Shop the oils'}})

add('anchor', {'type': 'custom-liquid', 'settings': {'liquid': '<span id="ingredients"></span>', 'color_scheme': 'scheme-1', 'remove_vertical_spacing': True, 'remove_horizontal_spacing': True}})

blocks = {}; bo = []
for ci, ((cat, icon), items) in enumerate(glossary.items(), 1):
  blocks[f'cat-{ci}'] = {'type': 'category', 'settings': {'title': cat, 'icon': icon, 'icon_width': 20}}; bo.append(f'cat-{ci}')
  for qi, (name, text) in enumerate(items, 1):
    blocks[f'ing-{ci}-{qi}'] = {'type': 'question', 'settings': {'question': name, 'answer': f'<p>{text}</p>'}}; bo.append(f'ing-{ci}-{qi}')
add('glossary', {'type': 'faq', 'blocks': blocks, 'block_order': bo,
  'settings': {'color_scheme': 'scheme-1', 'separate_section_with_border': False, 'show_categories': True, 'subheading': 'Reference', 'title': 'Our anthology of ingredients',
               'content': '<p>The naturally occurring compounds found across our formulations, each one derived from plants, resins, fruits, and seeds with a long history in biblical tradition. Tap a name to read about it.</p>'}})

add('closing', {'type': 'rich-text', 'blocks': {
  'head': {'type': 'heading', 'settings': {'text': 'Where the science of nature meets the nature of faith', 'heading_tag': 'h2'}},
  'verse': {'type': 'richtext', 'settings': {'content': '<p><em>\u201cThou anointest my head with oil; my cup runneth over.\u201d</em> Psalm 23:5</p>'}},
  'shop': {'type': 'button', 'settings': {'style': 'solid', 'text': 'Shop the collection', 'url': 'shopify://collections/all'}},
  'faq': {'type': 'link', 'settings': {'text': 'Questions? Read the FAQ', 'url': 'shopify://pages/faqs'}},
}, 'block_order': ['head', 'verse', 'shop', 'faq'],
  'settings': {'color_scheme': 'scheme-3', 'separate_section_with_border': False, 'content_width': 'sm', 'text_position': 'center', 'remove_vertical_spacing': False}})

tpl = {'sections': sections, 'order': order}
out = json.dumps(tpl, indent=2, ensure_ascii=False)
bad = [c for c in out if c in '—–']
assert not bad, 'dash found'
open(S + '/work/templates/page.our-science.json', 'w', encoding='utf-8').write(out + '\n')

# ---- page body (fallback for other themes / search engines), same copy, no inline styles
def h2(t): return f'<h2>{html.escape(t)}</h2>\n'
body = ''
body += h2('The science of sacred botanicals') + hero_text + '\n'
body += h2('Olive-derived squalane: the base of every oil') + squalane_tab + '\n'
body += h2(PA + ': our proprietary complex') + pa_tab.replace('<p><a href="#ingredients">Read the full ingredient glossary</a></p>', '') + '\n'
body += h2('Naturally derived. Scripturally rooted.') + botanicals_tab + '\n'
body += h2('Our formulation standards') + standards_tab + '\n'
body += h2('Our anthology of ingredients') + '<p><em>A reference of the naturally occurring compounds found across our formulations, each one derived from plants, resins, fruits, and seeds with a long history in biblical tradition.</em></p>\n'
for (cat, icon), items in glossary.items():
  body += f'<h3>{html.escape(cat)}</h3>\n'
  for name, text in items:
    body += f'<p><strong>{html.escape(name)}</strong>. {text}</p>\n'
body += '<p><em>\u201cThou anointest my head with oil; my cup runneth over.\u201d Psalm 23:5</em></p>\n<p><em>Mount of Olives. Where the science of nature meets the nature of faith.</em></p>\n'
assert not [c for c in body if c in '—–']
open(S + '/science/body.html', 'w', encoding='utf-8').write(body)
print('template bytes', len(out.encode()), 'sections', order, 'body bytes', len(body.encode()))
