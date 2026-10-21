# Builds templates/page.our-science.json for the Prestige work copy and the matching page body (no em dashes anywhere).
import json, re, sys, html
S = '.'  # theme folder: templates/ and the page body are written under it
IMG = 'shopify://shop_images/'
P = {  # products
  'olive': '/products/100-squalane', 'frank': '/products/frankincense', 'myrrh': '/products/myrrh-anointing-oil-1',
  'pom': '/products/pomegranate-anointing-oil', 'hyssop': '/products/hyssop', 'spike': '/products/spikenard-anointing-oil',
  'rose': '/products/rose-of-sharon', 'lily': '/products/lily-of-the-valley', 'fm': '/products/frankincense-myrrh-anointing-oil',
}
PA = 'Polyphenol Alpha (α)™'

hero_text = (
  '<p><em>Where cosmeceutical science meets the wisdom of Scripture.</em></p>'
  '<p>At Mount of Olives we formulate where modern dermatological science meets the botanical wisdom found throughout Scripture. '
  'Every product in our collection begins with the same plants, resins and extracts that have been revered for millennia: '
  '<strong>frankincense, myrrh, spikenard, hyssop, pomegranate, rose of Sharon and lily of the valley</strong>. '
  'We then elevate them through evidence-based cosmeceutical formulation.</p>'
  '<p>The result is a line of anointing oils that honors the sacred tradition of biblical anointing while delivering clinically meaningful '
  'concentrations of polyphenols, terpenes and bioactive compounds to the skin.</p>'
)

standards = [
  ('picto-leaf', 'Naturally derived actives', 'Every bioactive compound comes from a plant, resin, fruit or seed. Nothing is synthesized in a lab.'),
  ('picto-not-allowed', 'Free from the usual suspects', 'No parabens, phthalates, sulfates or synthetic fragrances.'),
  ('picto-shield', 'Kind to skin', 'Non-comedogenic and formulated with the skin’s natural microbiome in mind.'),
  ('picto-love', 'Cruelty-free', 'We honor all of God’s creation and never test on animals.'),
  ('picto-recycle', 'Honest and sustainable', 'Recyclable, biodegradable packaging, and every compound published with its botanical origin.'),
]

squalane_tab = (
  '<p>We formulate our anointing oils in a base of <strong>100% olive-derived squalane</strong>, a naturally occurring lipid that is bioidentical to the squalene already present in human skin. This is not a coincidence. It is by design.</p>'
  '<p>Squalane is far more than a moisturizer. As a <strong>high-performance delivery vehicle</strong> it improves the <strong>bioavailability</strong> of every botanical extract in our formulations. '
  'Its molecular weight and lipophilic structure let it move through the stratum corneum efficiently, carrying our polyphenol complex and active botanical compounds deeper into the skin, where they can do their full work. '
  'The result is better absorption, longer-lasting hydration and measurably greater efficacy, without synthetic penetration enhancers, chemical solvents or artificial emulsifiers.</p>'
  '<p>Squalane comes from the fruit of the olive tree, a tree that appears in Scripture more than any other. It ties our delivery science directly to the biblical tradition of olive oil anointing.</p>'
  f'<p><a href="{P["olive"]}">Shop 100% Squalane</a></p>'
)
pa_tab = (
  f'<p>Central to every Mount of Olives formulation is <strong>{PA}</strong>, our proprietary antioxidant-rich polyphenol complex, derived entirely from natural botanical sources. '
  'This carefully calibrated blend harnesses the combined activity of multiple polyphenolic compounds: flavonoids, phenolic acids, stilbenes and lignans. '
  'Each was selected for its demonstrated capacity to neutralize free radicals, support the skin’s natural barrier function and promote cellular vitality.</p>'
  f'<p>{PA} is not a single ingredient. It is an <strong>orchestrated matrix of bioactives</strong> working in concert, much the way Scripture describes the body: <em>“many parts, but one body”</em> (1 Corinthians 12:20). '
  'Each compound amplifies the others through complementary mechanisms of action, so the complex is greater than the sum of its parts.</p>'
  '<p><a href="#ingredients">Read the full ingredient glossary</a></p>'
)
botanicals_tab = (
  '<p>Every active compound in our formulations is a <strong>natural derivative</strong> of a plant, resin, fruit or seed with deep biblical significance.</p>'
  '<ul>'
  f'<li><strong>Boswellic acids</strong> from <em>Boswellia serrata</em> (<a href="{P["frank"]}">frankincense</a>): anti-inflammatory terpenes from the resin of the Magi</li>'
  f'<li><strong>Terpenoids and sesquiterpenes</strong> from <em>Commiphora myrrha</em> (<a href="{P["myrrh"]}">myrrh</a>): antimicrobial and regenerative compounds from the resin of purification</li>'
  f'<li><strong>Ellagitannins and punicalagins</strong> from <em>Punica granatum</em> (<a href="{P["pom"]}">pomegranate</a>): potent antioxidants from one of the seven blessed fruits of the Promised Land</li>'
  f'<li><strong>Hydroxytyrosol and oleuropein</strong> from <em>Olea europaea</em> (<a href="{P["olive"]}">olive</a>): among the most powerful natural antioxidants ever measured, from the tree of peace</li>'
  f'<li><strong>Apigenin and flavonoids</strong> from <em>Hyssopus officinalis</em> (<a href="{P["hyssop"]}">hyssop</a>): anti-inflammatory actives from the herb of purification (Psalm 51:7)</li>'
  f'<li><strong>Jatamansone and sesquiterpenes</strong> from <em>Nardostachys jatamansi</em> (<a href="{P["spike"]}">spikenard</a>): neuroprotective and skin-soothing compounds from the precious oil of Mary of Bethany</li>'
  f'<li><strong>Labdanum and polyphenols</strong> from <em>Cistus ladaniferus</em> (<a href="{P["rose"]}">rose of Sharon</a>): regenerative and astringent actives from the flower of Song of Solomon</li>'
  '</ul>'
  '<p>These are not synthetic analogs or lab-created substitutes. They are the <strong>authentic molecular constituents</strong> of the very plants Scripture names, isolated, concentrated and formulated for optimal dermal delivery.</p>'
)
standards_tab = (
  '<p>We do not synthesize our actives in a laboratory. We extract, purify and concentrate them from the same botanical sources that God placed in creation.</p>'
  '<p>What we place on our bodies, temples of the Holy Spirit, should meet the highest standards of both purity and performance. Our commitment:</p>'
  '<ul>'
  '<li><strong>100% naturally derived active ingredients.</strong> Every bioactive compound originates from a botanical source.</li>'
  '<li><strong>Free from parabens, phthalates, sulfates and synthetic fragrances.</strong> We exclude ingredients that do not align with our values or our science.</li>'
  '<li><strong>Non-comedogenic, dermatologist-conscious formulation.</strong> Designed to nourish without disrupting the skin’s natural microbiome.</li>'
  '<li><strong>Cruelty-free.</strong> We honor all of God’s creation and never test on animals.</li>'
  '<li><strong>Sustainable, eco-conscious packaging.</strong> Recyclable and biodegradable materials, as part of our stewardship of the earth.</li>'
  '<li><strong>Full ingredient transparency.</strong> We publish every compound and its botanical origin, because informed customers are empowered customers.</li>'
  '</ul>'
)

cards = [  # (image file, title, text, link text, link)
  ('olive-trees-gethsemane-mount-of-olives.jpg', 'Olive', 'Olea europaea', 'Hydroxytyrosol and oleuropein, among the most powerful natural antioxidants ever measured, from the tree Scripture names more than any other. Also the source of our squalane base.', 'Shop 100% Squalane', P['olive']),
  ('frankincense-bible-sacred-resin-anointing-spiritual-healing.jpg', 'Frankincense', 'Boswellia serrata', 'Boswellic acids, anti-inflammatory terpenes from the resin the Magi brought (Matthew 2:11).', 'Shop Frankincense', P['frank']),
  ('myrrh-bible-ancient-oil-healing-anointing.jpg', 'Myrrh', 'Commiphora myrrha', 'Terpenoids and sesquiterpenes, antimicrobial and regenerative compounds from the resin of purification.', 'Shop Myrrh', P['myrrh']),
  ('a-beautiful-ripe-pomegranate-split-open-revealing-ruby-red-seeds-on-a-rustic-wooden-surface-with-a-small-glass-bottle-of-golden-anointing-oil-beside-it-warm-golden-light-biblical-abun.png', 'Pomegranate', 'Punica granatum', 'Ellagitannins and punicalagins, potent antioxidants from one of the seven blessed fruits of the Promised Land (Deuteronomy 8:8).', 'Shop Pomegranate', P['pom']),
  ('hyssop-bible-sacred-herb-purification-cleansing.jpg', 'Hyssop', 'Hyssopus officinalis', 'Apigenin and flavonoids, anti-inflammatory actives from the herb of purification (Psalm 51:7).', 'Shop Hyssop', P['hyssop']),
  ('spikenard-bible-precious-oil-mary-anointed-jesus.jpg', 'Spikenard', 'Nardostachys jatamansi', 'Jatamansone and sesquiterpenes, neuroprotective and skin-soothing compounds from the precious oil of Mary of Bethany (John 12:3).', 'Shop Spikenard', P['spike']),
  ('rose-of-sharon-biblical-flower-healing.jpg', 'Rose of Sharon', 'Cistus ladaniferus', 'Labdanum and polyphenols, regenerative and astringent actives from the flower of Song of Solomon 2:1.', 'Shop Rose of Sharon', P['rose']),
  ('beautiful-lily-of-the-valley-flowers-with-delicate-white-bell-shaped-blossoms-on-green-stems-soft-golden-light-a-small-glass-bottle-of-anointing-oil-nearby-warm-spiritual-atmosphere-b.png', 'Lily of the Valley', 'Song of Solomon 2:1', 'Named in the same verse as the rose of Sharon. Carried on the same olive squalane base as every oil in the line.', 'Shop Lily of the Valley', P['lily']),
]

timeline = [  # (image, label, subheading, title, content, link text, link url)
  ('ornate-ancient-vessels-of-gold-frankincense-resin-and-myrrh-presented-as-gifts-on-rich-fabric-glowing-star-of-bethlehem-in-the-night-sky-through-an-open-window-warm-golden-candlelight.png', '01', 'Rooted in Scripture', 'The plants come first',
   '<p>Every product begins with the plants, resins and extracts Scripture names: frankincense, myrrh, spikenard, hyssop, pomegranate, rose of Sharon and lily of the valley.</p>', '', ''),
  ('ancient-sacred-anointing-oil-ingredients-from-exodus-30-arranged-on-a-stone-altar-myrrh-resin-cinnamon-sticks-cassia-bark-and-olive-oil-in-a-golden-vessel-warm-candlelight-holy-tabern.png', '02', 'Extracted, not synthesized', 'The real compounds of the plant',
   '<p>We extract, purify and concentrate the actives from the same botanical sources God placed in creation. They are the authentic molecular constituents of the plants, not lab-made substitutes.</p>', '', ''),
  ('squalane1oz.jpg', '03', 'Carried by olive squalane', 'Deeper, with nothing synthetic',
   '<p>Each extract is carried in 100% olive-derived squalane, a lipid bioidentical to the squalene in your own skin. It takes the botanical compounds deeper, without synthetic penetration enhancers, chemical solvents or artificial emulsifiers.</p>', 'About 100% Squalane', P['olive']),
  ('praying-with-frankincense-myrrh.jpg', '04', 'Made for anointing', 'Science in service of faith',
   '<p>The result honors the sacred tradition of biblical anointing while nourishing the skin with clinically meaningful concentrations of polyphenols, terpenes and bioactive compounds.</p>', 'Shop the collection', 'shopify://collections/all'),
]

glossary = {
  ('From the olive', 'picto-tree'): [
    ('Hydroxytyrosol', 'An ortho-diphenol found mainly in olives and olive oil. Regarded as one of the most potent natural antioxidants measured by ORAC value, with exceptional capacity for neutralizing reactive oxygen species and protecting lipid membranes from peroxidation.'),
    ('Tyrosol', 'A phenolic antioxidant found in olives, olive oil and wine. It protects against lipid peroxidation and oxidative stress, supporting long-term skin health and resilience.'),
    ('Oleuropein-aglycone dialdehyde', 'A secoiridoid polyphenol from olives with potent antioxidant and anti-inflammatory properties. It helps protect dermal collagen and elastin fibers.'),
    ('Oleuropein-aglycone mono-aldehyde', 'A structurally related olive secoiridoid with complementary antioxidant activity. It strengthens the polyphenolic defense matrix in our formulations.'),
    ('Ligstroside-aglycone di-aldehyde', 'A secoiridoid compound found in olives and extra virgin olive oil. It scavenges peroxyl radicals and supports protection against environmentally induced oxidative damage.'),
    ('Pinoresinol', 'A lignan found in olives, olive oil and sesame seeds. It has antioxidant activity and may support the skin’s resistance to environmental aging by moderating oxidative stress pathways.'),
    ('Olive oil (Olea europaea)', 'Cold-pressed from the fruit of the olive tree, the most frequently referenced tree in all of Scripture. Rich in oleic acid, squalene, hydroxytyrosol and tocopherols. It is both a nourishing emollient and a natural source of the bioactive compounds central to our ' + PA + ' complex.'),
    ('Squalane (olive-derived)', 'A fully saturated, stable hydrocarbon obtained by hydrogenating squalene extracted from Olea europaea (olive). Bioidentical to the squalene naturally present in human sebum, it works as a superior emollient, an occlusive moisturizer and a lipophilic delivery vehicle that greatly improves the absorption and bioavailability of our botanical actives. Non-comedogenic, odorless and oxidatively stable: the ideal carrier for our ' + PA + ' complex.'),
  ],
  ('Resins: frankincense and myrrh', 'picto-gift'): [
    ('Boswellia serrata (frankincense)', 'A pentacyclic triterpenic resin from the bark of the Boswellia serrata tree, native to India and the Middle East. It contains boswellic acids (AKBA and KBA), potent inhibitors of 5-lipoxygenase with demonstrated anti-inflammatory and analgesic properties. One of the three gifts the Magi presented to the Christ child (Matthew 2:11) and a cornerstone of ancient anointing formulations.'),
    ('Commiphora myrrha (myrrh)', 'An oleoresin harvested from the Commiphora myrrha tree of the Arabian Peninsula and northeastern Africa. It contains terpenoids (curzerene, furanoeudesma-1,3-diene), sesquiterpenes and flavonoids with validated anti-inflammatory, antioxidant and antimicrobial efficacy. A gift of the Magi and a biblical symbol of purification, consecration and healing.'),
    ('Botanical resins', 'Natural oleoresins from frankincense, myrrh and labdanum. They contain complex mixtures of terpenes, sesquiterpenes and phenolic acids with astringent, antimicrobial and wound-healing properties, used in traditional formulations for millennia.'),
  ],
  ('Herbs and flowers', 'picto-leaf'): [
    ('Hyssopus officinalis (hyssop)', 'The biblical herb of purification named in Psalm 51:7: “Purge me with hyssop, and I shall be clean.” It contains apigenin, rosmarinic acid and essential oil terpenes with demonstrated antioxidant, anti-inflammatory and antimicrobial properties for skin health.'),
    ('Nardostachys jatamansi (spikenard)', 'The precious aromatic rhizome Mary of Bethany used to anoint Jesus before his burial (John 12:3). It contains jatamansone, nardosinone and sesquiterpene compounds with documented neuroprotective, anti-inflammatory and skin-soothing properties. One of the rarest and most valued botanicals in our collection.'),
    ('Cistus ladaniferus (rose of Sharon)', 'The labdanum-producing Mediterranean shrub referenced as the rose of Sharon in Song of Solomon 2:1. Rich in polyphenolic compounds with documented astringent, antimicrobial and tissue-regenerative properties.'),
  ],
  ('Pomegranate', 'picto-star'): [
    ('Punica granatum (pomegranate)', 'One of the seven species blessed in the Torah (Deuteronomy 8:8). The fruit and seed contain ellagitannins, punicalagins A and B, punicalin, gallic acid and ellagic acid: a remarkably dense polyphenolic profile with antioxidant, anti-inflammatory and collagen-supportive benefits for skin elasticity and firmness.'),
    ('Ellagitannins', 'Hydrolyzable tannins found in pomegranates, raspberries and walnuts. They are metabolized to ellagic acid and urolithins, which show potent antioxidant, anti-inflammatory and anti-aging activity through modulation of NF-κB signaling pathways.'),
  ],
  ('The wider polyphenol family', 'picto-shield'): [
    ('Apigenin', 'A flavonoid naturally present in parsley (Petroselinum crispum), chamomile (Matricaria chamomilla), celery (Apium graveolens) and hyssop (Hyssopus officinalis). It has antioxidant and anti-inflammatory activity that helps reduce oxidative stress and inflammation in skin tissue.'),
    ('Caffeic acid', 'A hydroxycinnamic acid found in coffee, wine and many botanical sources. It acts as an antioxidant through free radical scavenging and metal chelation, supporting the skin’s defense against photooxidative damage.'),
    ('Catechin', 'A flavan-3-ol polyphenol abundant in tea (Camellia sinensis) and many fruits. It provides broad-spectrum antioxidant protection and supports collagen integrity by inhibiting matrix metalloproteinases (MMPs).'),
    ('Chlorogenic acid', 'A phenolic compound found in coffee and stone fruits. An antioxidant and UV-absorbing agent that contributes photoprotective and anti-inflammatory skin benefits.'),
    ('Epicatechin', 'A flavanol found in tea and cocoa with demonstrated antioxidant capacity. It supports skin barrier integrity and microcirculation.'),
    ('Ferulic acid', 'A phenolic compound from rice bran, wheat and oats. A potent UV-absorbing antioxidant that improves the stability and efficacy of the other antioxidants in a formulation. A key component of our ' + PA + ' complex.'),
    ('Gallic acid', 'A trihydroxybenzoic acid found in grapes, tea leaves and oak bark. It has antioxidant, anti-inflammatory and antiproliferative properties that contribute to comprehensive skin protection.'),
    ('Homovanillic acid', 'A phenolic compound found in vanilla beans and select botanical sources. Its antioxidant activity may contribute to free radical defense in skin tissue.'),
    ('Isoquercitrin', 'A quercetin glycoside found in apples, onions and various botanical sources. It is more bioavailable than free quercetin, with antioxidant and anti-inflammatory activity that supports skin resilience.'),
    ('Luteolin', 'A flavone found in celery, parsley and thyme. It has potent anti-inflammatory activity through inhibition of pro-inflammatory cytokines and supports the skin’s UV-protective mechanisms.'),
    ('Quercetin', 'One of the most abundant dietary flavonoids, found in apples, onions, berries and tea. A powerful antioxidant and anti-inflammatory agent that moderates histamine release and supports the skin’s defense against UV-induced photodamage.'),
    ('Quercitrin (quercetin-3-rhamnoside)', 'A quercetin glycoside with enhanced bioavailability, found in citrus fruits and berries. It adds complementary antioxidant and anti-inflammatory activity within our polyphenol matrix.'),
    ('Rutin', 'A flavonoid glycoside found in buckwheat, apples and citrus. It supports capillary integrity and provides antioxidant protection, contributing to an even, healthy-looking complexion.'),
  ],
}

closing_text = ('<p>Scripture describes the body as “many parts, but one body” (1 Corinthians 12:20). Our oils work the same way: many compounds, one complex, carried in one olive base.</p>')

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
  'settings': {'color_scheme': 'scheme-2', 'separate_section_with_border': False, 'subheading': 'Inside every bottle', 'title': 'Two things make our oils different', 'text_alignment': 'center'}})

blocks = {}; bo = []
for i, (img, title, latin, text, lt, lu) in enumerate(cards, 1):
  blocks[f'plant-{i}'] = {'type': 'image_with_text', 'settings': {'image': IMG + img, 'title': title, 'heading_tag': 'h3', 'content': f'<p><em>{latin}</em></p><p>{text}</p>', 'link_url': lu, 'link_text': lt}}; bo.append(f'plant-{i}')
add('botanicals', {'type': 'multi-column', 'blocks': blocks, 'block_order': bo,
  'settings': {'color_scheme': 'scheme-1', 'separate_section_with_border': False, 'columns_per_row': 4, 'stack_on_mobile': False, 'overlap_image': False,
               'content_alignment': 'start', 'text_alignment': 'start', 'spacing': 'md', 'subheading': 'From creation', 'title': 'The plants Scripture names',
               'content': '<p>Each oil carries the real compounds of its plant. Tap a botanical to shop its oil.</p>'}})

look1 = [('rose-of-sharon', 17), ('latter-rain-anointing-oil', 41), ('hyssop', 65), ('spikenard-anointing-oil', 88)]
look2 = [('lily-of-the-valley', 11), ('frankincense-myrrh-anointing-oil', 37), ('pomegranate-anointing-oil', 60), ('gethsemane-anointing-oil-unscented', 84)]
def look(img, prods):
  s = {'image': IMG + img, 'hot_spots_background': '#c4a265'}
  for i, (h, x) in enumerate(prods, 1):
    s[f'product_{i}'] = h; s[f'product_{i}_horizontal_position'] = x; s[f'product_{i}_vertical_position'] = 33
  return {'type': 'look', 'settings': s}
add('look', {'type': 'shop-the-look', 'blocks': {'look-1': look('mo-science-look-1.jpg', look1), 'look-2': look('mo-science-look-2.jpg', look2)}, 'block_order': ['look-1', 'look-2'],
  'settings': {'color_scheme': 'scheme-2', 'separate_section_with_border': False, 'subheading': 'The collection', 'title': 'Tap a bottle',
               'content': '<p>Every oil is built on the same olive squalane base. Tap a dot to see the oil and add it to your cart.</p>', 'popover_title': 'Shop the oils'}})

add('anchor', {'type': 'custom-liquid', 'settings': {'liquid': '<span id="ingredients"></span>', 'color_scheme': 'scheme-1', 'remove_vertical_spacing': True, 'remove_horizontal_spacing': True}})

blocks = {}; bo = []
for ci, ((cat, icon), items) in enumerate(glossary.items(), 1):
  blocks[f'cat-{ci}'] = {'type': 'category', 'settings': {'title': cat, 'icon': icon, 'icon_width': 20}}; bo.append(f'cat-{ci}')
  for qi, (name, text) in enumerate(items, 1):
    blocks[f'ing-{ci}-{qi}'] = {'type': 'question', 'settings': {'question': name, 'answer': f'<p>{text}</p>'}}; bo.append(f'ing-{ci}-{qi}')
add('glossary', {'type': 'faq', 'blocks': blocks, 'block_order': bo,
  'settings': {'color_scheme': 'scheme-1', 'separate_section_with_border': False, 'show_categories': True, 'subheading': 'Reference', 'title': 'Our anthology of ingredients',
               'content': '<p>The naturally occurring bioactive compounds found across our formulations. Each one is derived from plants, resins, fruits and seeds with documented use in both biblical tradition and modern dermatological research. Tap a name to read about it.</p>'}})

add('closing', {'type': 'rich-text', 'blocks': {
  'head': {'type': 'heading', 'settings': {'text': 'Where the science of nature meets the nature of faith', 'heading_tag': 'h2'}},
  'text': {'type': 'richtext', 'settings': {'content': closing_text}},
  'shop': {'type': 'button', 'settings': {'style': 'solid', 'text': 'Shop the collection', 'url': 'shopify://collections/all'}},
  'faq': {'type': 'link', 'settings': {'text': 'Questions? Read the FAQ', 'url': 'shopify://pages/faqs'}},
}, 'block_order': ['head', 'text', 'shop', 'faq'],
  'settings': {'color_scheme': 'scheme-3', 'separate_section_with_border': False, 'content_width': 'sm', 'text_position': 'center', 'remove_vertical_spacing': False}})

tpl = {'sections': sections, 'order': order}
out = json.dumps(tpl, indent=2, ensure_ascii=False)
bad = [c for c in out if c in '—–']
assert not bad, 'dash found'
open(S + '/templates/page.our-science.json', 'w', encoding='utf-8').write(out + '\n')

# ---- page body (fallback for other themes / search engines), same copy, no inline styles
def h2(t): return f'<h2>{html.escape(t)}</h2>\n'
body = ''
body += h2('The science of sacred botanicals') + hero_text + '\n'
body += h2('Olive-derived squalane: the bioavailability carrier') + squalane_tab + '\n'
body += h2(PA + ': our proprietary complex') + pa_tab.replace('<p><a href="#ingredients">Read the full ingredient glossary</a></p>', '') + '\n'
body += h2('Naturally derived. Scripturally rooted. Scientifically validated.') + botanicals_tab + '\n'
body += h2('Our formulation standards') + standards_tab + '\n'
body += h2('Our anthology of ingredients') + '<p><em>A reference of the naturally occurring bioactive compounds found across our formulations. Each one is derived from plants, resins, fruits and seeds with documented use in both biblical tradition and modern dermatological research.</em></p>\n'
for (cat, icon), items in glossary.items():
  body += f'<h3>{html.escape(cat)}</h3>\n'
  for name, text in items:
    body += f'<p><strong>{html.escape(name)}</strong>. {text}</p>\n'
body += '<p><em>Mount of Olives. Where the science of nature meets the nature of faith.</em></p>\n'
assert not [c for c in body if c in '—–']
open(S + '/our-science-body.html', 'w', encoding='utf-8').write(body)
print('template bytes', len(out.encode()), 'sections', order, 'body bytes', len(body.encode()))
