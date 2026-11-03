"""Cockpit d'usine : socle ERP, suivi de production, qualité et traçabilité.

    streamlit run app/app.py
"""
from __future__ import annotations

import textwrap

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sfe import checks, kpi  # noqa: E402
from sfe import masterdata as md  # noqa: E402
from sfe.db import DB, build, query  # noqa: E402

st.set_page_config(page_title="Usine M1 : cockpit ERP", page_icon="🏭", layout="wide")

GREEN, LEAF, SAND, CORAL, AMBER, SLATE, INK = "#12372A", "#3E9B6E", "#F4EFE6", "#E4572E", "#F2A541", "#5B6B73", "#1E2A2F"
PALETTE = [LEAF, AMBER, CORAL, SLATE, "#8FB9A8", "#C9A66B"]

st.markdown(f"""
<style>
  .stApp {{ background: {SAND}; }}
  section[data-testid="stSidebar"] {{ background: {GREEN}; }}
  section[data-testid="stSidebar"] * {{ color: #EAF3EE !important; }}
  h1, h2, h3 {{ color: {GREEN}; letter-spacing: -0.01em; }}
  .hero {{ background: linear-gradient(120deg, {GREEN} 0%, #1F5A44 60%, {LEAF} 100%); color: white;
          border-radius: 18px; padding: 26px 30px; margin-bottom: 18px; }}
  .hero h1 {{ color: white; margin: 0 0 4px 0; font-size: 30px; }}
  .hero p {{ margin: 0; opacity: .9; font-size: 15px; }}
  .kpi {{ background: white; border-radius: 16px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(18,55,42,.10);
          border-left: 6px solid {LEAF}; min-height: 118px; }}
  .kpi .lab {{ color: {SLATE}; font-size: 13px; text-transform: uppercase; letter-spacing: .04em; }}
  .kpi .val {{ color: {INK}; font-size: 30px; font-weight: 700; margin-top: 2px; }}
  .kpi .sub {{ color: {SLATE}; font-size: 13px; }}
  .kpi .val.txt {{ font-size: 21px; line-height: 1.25; margin: 6px 0 4px 0; }}
  .kpi.warn {{ border-left-color: {AMBER}; }} .kpi.bad {{ border-left-color: {CORAL}; }}
  .station {{ background: white; border-radius: 16px; padding: 14px 16px; text-align: center;
              box-shadow: 0 1px 3px rgba(18,55,42,.10); border-top: 6px solid {LEAF}; }}
  .station.warn {{ border-top-color: {AMBER}; }} .station.bad {{ border-top-color: {CORAL}; }}
  .station .nm {{ font-weight: 700; color: {GREEN}; font-size: 15px; }}
  .station .big {{ font-size: 34px; font-weight: 800; color: {INK}; }}
  .station .sm {{ color: {SLATE}; font-size: 12.5px; }}
  .arrow {{ text-align: center; font-size: 30px; color: {LEAF}; padding-top: 38px; }}
  .note {{ background: white; border-radius: 14px; padding: 14px 18px; border: 1px solid #E4DED2; }}
  .tag {{ display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 12px; font-weight: 600;
          background: #E3F1E9; color: {GREEN}; margin-right: 6px; }}
  .tag.red {{ background: #FBE3DC; color: #9C2F14; }} .tag.amber {{ background: #FCEFD9; color: #8A5A0B; }}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def ensure_db():
    if not DB.exists():
        build()
    return str(DB)


ensure_db()


def pct(x, d=0):
    return f"{100 * x:.{d}f} %".replace(".", ",")


def kpi_card(col, label, value, sub="", level=""):
    cls = "val txt" if len(str(value)) > 11 else "val"
    col.markdown(f'<div class="kpi {level}"><div class="lab">{label}</div><div class="{cls}">{value}</div>'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def style(fig, h=340, legend=True):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=48, b=10), paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family="Inter, Segoe UI, sans-serif", color=INK, size=13),
                      legend=dict(orientation="h", yanchor="top", y=-0.16, x=0) if legend else dict(visible=False),
                      title_font=dict(size=16, color=GREEN))
    fig.update_xaxes(gridcolor="#EEE9DF", zeroline=False)
    fig.update_yaxes(gridcolor="#EEE9DF", zeroline=False)
    return fig


def hero(title, text):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{text}</p></div>', unsafe_allow_html=True)


# ====================================================================== pages
def page_direction():
    hero("Usine M1 : 8 premières semaines", "Mixeur réparable M1 et M1 Plus · ligne de 4 postes · vue direction "
         "hebdomadaire. Données simulées pour démontrer le socle ERP et le pilotage.")
    h = kpi.headline()
    c = st.columns(5)
    kpi_card(c[0], "TRS de la ligne", pct(h["trs_last"]), f"semaine 1 : {pct(h['trs_first'])}")
    kpi_card(c[1], "Respect des délais", pct(h["otd_last"]), f"semaine 2 : {pct(h['otd_first'])}",
             "" if h["otd_last"] > .95 else "warn")
    kpi_card(c[2], "Taux de rebut", pct(h["scrap_last"], 1), f"semaine 1 : {pct(h['scrap_first'], 1)}",
             "" if h["scrap_last"] < .025 else "warn")
    kpi_card(c[3], "Taux de service", pct(h["service_last"]), "quantités livrées à l'heure")
    kpi_card(c[4], "Mixeurs livrés", f"{h['expédiés']:,}".replace(",", " "), f"sur {h['produits']:,} fabriqués"
             .replace(",", " "))
    st.write("")

    t, s, q = kpi.trs_week(), kpi.service_week(), kpi.quality_week()
    a, b = st.columns([1.35, 1])
    fig = go.Figure()
    for name, color in (("disponibilité", SLATE), ("performance", AMBER), ("qualité", "#8FB9A8")):
        fig.add_scatter(x=t.semaine, y=t[name], name=name, mode="lines", line=dict(color=color, width=2, dash="dot"))
    fig.add_bar(x=t.semaine, y=t.TRS, name="TRS", marker_color=LEAF, text=[pct(v) for v in t.TRS],
                textposition="outside", opacity=.95)
    fig.update_layout(title="Montée en cadence : TRS du poste goulot (assemblage)", yaxis_tickformat=".0%",
                      yaxis_range=[0, 1.08], xaxis_title="semaine")
    a.plotly_chart(style(fig, 380), width="stretch")
    lo = kpi.losses()
    wf = go.Figure(go.Waterfall(x=["<br>".join(textwrap.wrap(x, 10, break_long_words=False, break_on_hyphens=False)) for x in lo.poste], y=lo.heures, measure=["absolute", "relative", "relative", "relative",
                                                                    "total"],
                                connector=dict(line=dict(color="#CFC7B8")),
                                increasing=dict(marker_color=LEAF), decreasing=dict(marker_color=CORAL),
                                totals=dict(marker_color=GREEN), text=[f"{abs(v):.0f} h" for v in lo.heures],
                                textposition="outside"))
    wf.update_layout(title="Où passe le temps du goulot (8 semaines)", yaxis_title="heures", xaxis_tickangle=0)
    b.plotly_chart(style(wf, 380, legend=False), width="stretch")

    a, b = st.columns(2)
    fig = go.Figure()
    fig.add_bar(x=s.semaine, y=s["respect des délais"], name="respect des délais", marker_color=GREEN)
    fig.add_scatter(x=s.semaine, y=s["taux de service"], name="taux de service", mode="lines+markers",
                    line=dict(color=AMBER, width=3))
    fig.update_layout(title="Livraisons clients : le retard des précommandes résorbé en semaine 4",
                      yaxis_tickformat=".0%", xaxis_title="semaine d'échéance")
    a.plotly_chart(style(fig), width="stretch")
    fig = go.Figure()
    fig.add_bar(x=q.semaine, y=q["taux de rebut"], name="taux de rebut", marker_color=CORAL)
    fig.add_scatter(x=q.semaine, y=q["rendement 1er passage"], name="rendement au 1er passage", yaxis="y2",
                    mode="lines+markers", line=dict(color=LEAF, width=3))
    fig.update_layout(title="Qualité : la semaine 5 révèle un lot de roulements défectueux", yaxis_tickformat=".1%",
                      yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0.85, 1]),
                      xaxis_title="semaine")
    b.plotly_chart(style(fig), width="stretch")
    st.markdown('<div class="note"><b>Lecture.</b> Le TRS du goulot passe de 49 % à 78 % en huit semaines, porté '
                "par la performance (apprentissage des opérateurs) et la qualité. La chute de la semaine 6 vient "
                "d'une journée d'arrêt après la mise en quarantaine d'un lot de roulements : la traçabilité a permis "
                "de retrouver en quelques secondes les mixeurs concernés.</div>", unsafe_allow_html=True)


def page_atelier():
    hero("Vue atelier", "État de la ligne sur la journée choisie : TRS par poste, arrêts et production.")
    day = st.slider("Journée", 1, 40, 25)
    d = query("SELECT * FROM v_trs_poste_jour WHERE day = ?", params=(day,)).set_index("wc_id")
    names = {w[0]: w[1] for w in md.WORKCENTERS}
    cols = st.columns([1, .18, 1, .18, 1, .18, 1])
    for k, wc in enumerate(["WC-PRE", "WC-ASM", "WC-TST", "WC-EMB"]):
        r = d.loc[wc] if wc in d.index else None
        trs = 0 if r is None else (r.trs if pd.notna(r.trs) else 0)
        q = 1 if r is None or pd.isna(r.qualite) else r.qualite
        lvl = "" if trs >= .7 else "warn" if trs >= .5 else "bad"
        goulot = " · goulot" if wc == "WC-ASM" else ""
        if wc == "WC-ASM":
            big, lab = pct(trs), "TRS de la ligne"
            sub = (f"dispo {pct(r.disponibilite)} · perf {pct(r.performance)} · qualité {pct(q, 1)}"
                   if r is not None else "pas de production")
        else:
            big, lab = pct(q, 1), "qualité au poste"
            sub = (f"dispo {pct(r.disponibilite)} · charge {pct(r.performance)} (cadencé par le goulot)"
                   if r is not None else "pas de production")
            lvl = "" if q > .98 else "warn" if q > .9 else "bad"
        cols[2 * k].markdown(f'<div class="station {lvl}"><div class="nm">{names[wc]}</div>'
                             f'<div class="sm">{wc}{goulot}</div><div class="big">{big}</div>'
                             f'<div class="sm">{lab}</div><div class="sm">{sub}</div></div>', unsafe_allow_html=True)
        if k < 3:
            cols[2 * k + 1].markdown('<div class="arrow">➜</div>', unsafe_allow_html=True)
    st.write("")
    mo = query("SELECT mo.item_id, mo.qty, mo.status, i.name FROM manufacturing_order mo JOIN item i USING (item_id) "
               "WHERE day = ?", params=(day,))
    a, b, c = st.columns([1, 1.2, 1])
    with a:
        st.subheader("Ordres de fabrication")
        for _, r in mo.iterrows():
            tag = "tag red" if r.qty == 0 else "tag"
            st.markdown(f'<span class="{tag}">{r.status}</span> **{r["name"]}** : {r.qty} pièces',
                        unsafe_allow_html=True)
        nc = query("SELECT defect, COUNT(*) n FROM nonconformity WHERE day = ? AND stage <> 'réception' "
                   "GROUP BY defect ORDER BY n DESC", params=(day,))
        st.subheader("Non-conformités du jour")
        st.dataframe(nc.rename(columns={"defect": "défaut", "n": "nombre"}), hide_index=True, width="stretch")
    pa = kpi.downtime_pareto(day, day)
    fig = go.Figure(go.Bar(x=pa.heures, y=pa.cause, orientation="h", marker_color=[CORAL if "Manque" in c else AMBER
                                                                                     for c in pa.cause]))
    fig.update_layout(title="Arrêts du jour (tous postes)", xaxis_title="heures", yaxis_autorange="reversed")
    b.plotly_chart(style(fig, 330, legend=False), width="stretch")
    line = kpi.trs_line_day()
    fig = go.Figure(go.Scatter(x=line.day, y=line.trs, mode="lines", line=dict(color=LEAF, width=3), fill="tozeroy",
                               fillcolor="rgba(62,155,110,.15)"))
    fig.add_vline(x=day, line_color=CORAL, line_dash="dash")
    fig.update_layout(title="TRS du goulot, jour par jour", yaxis_tickformat=".0%")
    c.plotly_chart(style(fig, 330, legend=False), width="stretch")


def page_tracabilite():
    hero("Traçabilité", "D'un numéro de série vers ses lots et fournisseurs, ou d'un lot vers tous les mixeurs qui "
         "le contiennent et leurs clients.")
    bad = query("SELECT lot_id, day FROM receipt WHERE item_id = 'ROU-608' AND status = 'quarantaine'")
    lot_default = bad.lot_id.iloc[0] if not bad.empty else ""
    mode = st.radio("Recherche", ["Par lot fournisseur (rappel)", "Par numéro de série"], horizontal=True)
    if mode.startswith("Par lot"):
        lots = query("SELECT lot_id FROM receipt WHERE lot_id IN (SELECT DISTINCT lot_id FROM genealogy) "
                     "ORDER BY lot_id").lot_id.tolist()
        lot = st.selectbox("Lot", lots, index=lots.index(lot_default) if lot_default in lots else 0)
        info = query("""SELECT r.lot_id, i.name, r.qty, r.day, r.status, s.name fournisseur FROM receipt r
                        JOIN item i USING (item_id) JOIN purchase_order po ON po.po_id = r.po_id
                        JOIN supplier s ON s.supplier_id = po.supplier_id WHERE r.lot_id = ?""", params=(lot,)).iloc[0]
        t = kpi.trace_lot(lot)
        c = st.columns(4)
        kpi_card(c[0], "Composant", info["name"], f"{info.fournisseur} · reçu jour {info.day}")
        kpi_card(c[1], "Statut du lot", info.status, f"{info.qty:,} pièces reçues".replace(",", " "),
                 "bad" if info.status != "accepté" else "")
        kpi_card(c[2], "Mixeurs concernés", f"{len(t)}", "numéros de série contenant ce lot")
        shipped = t[t["jour d'expédition"].notna()]
        kpi_card(c[3], "Déjà chez le client", f"{len(shipped)}", "à rappeler ou surveiller",
                 "bad" if len(shipped) and info.status != "accepté" else "")
        st.write("")
        a, b = st.columns([1.1, 1])
        flows = t.groupby(["produit", "destination"]).size().reset_index(name="n")
        labels = [lot] + sorted(flows.produit.unique()) + sorted(flows.destination.unique())
        idx = {lab: i for i, lab in enumerate(labels)}
        src = [0] * flows.produit.nunique() + [idx[p] for p in flows.produit]
        tgt = [idx[p] for p in sorted(flows.produit.unique())] + [idx[d] for d in flows.destination]
        val = list(flows.groupby("produit").n.sum().sort_index()) + list(flows.n)
        fig = go.Figure(go.Sankey(node=dict(label=labels, pad=18, thickness=16,
                                            color=[CORAL] + [LEAF] * flows.produit.nunique()
                                            + [SLATE] * flows.destination.nunique()),
                                  link=dict(source=src, target=tgt, value=val, color="rgba(62,155,110,.25)")))
        fig.update_layout(title="Du lot au client")
        a.plotly_chart(style(fig, 380, legend=False), width="stretch")
        b.markdown("**Liste de rappel**")
        b.dataframe(t, hide_index=True, height=330, width="stretch")
        b.download_button("Exporter la liste (CSV pour Excel)",
                          t.to_csv(index=False, sep=";").encode("utf-8-sig"), f"rappel_{lot}.csv", "text/csv")
    else:
        first = query("SELECT serial_no FROM v_tracabilite WHERE lot_id = ? LIMIT 1", params=(lot_default,))
        sn = st.text_input("Numéro de série", first.serial_no.iloc[0] if not first.empty else "M1-00001",
                           help="Préfixe M1- ou M1P- suivi du rang de fabrication, toutes versions confondues "
                                "(ex. M1-00001, M1P-00077). Imprimé sur l'étiquette signalétique.")
        sn = sn.strip().upper()
        info = kpi.serial_info(sn)
        if info.empty:
            st.warning(f"Numéro de série « {sn} » inconnu. Exemples : M1-00001, M1P-00077." if sn else
                       "Saisissez ou scannez un numéro de série.")
            return
        r = info.iloc[0]
        c = st.columns(4)
        kpi_card(c[0], "Produit", r["name"], f"fabriqué jour {r.day} · {r.mo_id}")
        kpi_card(c[1], "Statut", r.status)
        kpi_card(c[2], "Client", "rebuté à l'usine" if r.status == "rebut" else r.customer or "en stock usine",
                 f"expédié jour {int(r.shipped_day)}" if pd.notna(r.shipped_day) else "")
        kpi_card(c[3], "Lots tracés", f"{len(kpi.trace_serial(sn))}", "composants suivis par lot")
        st.write("")
        a, b = st.columns(2)
        a.markdown("**Composition : lots et fournisseurs**")
        a.dataframe(kpi.trace_serial(sn), hide_index=True, width="stretch")
        b.markdown("**Résultats de contrôle**")
        b.dataframe(kpi.serial_tests(sn), hide_index=True, width="stretch")


def page_qualite():
    hero("Qualité", "Plans de contrôle, non-conformités, carte de contrôle du test final et 8D.")
    a, b = st.columns(2)
    pa = kpi.nc_pareto()
    fig = go.Figure()
    pa["lab"] = ["<br>".join(textwrap.wrap(d, 13, break_long_words=False)) for d in pa.defect]
    fig.add_bar(x=pa.lab, y=pa.n, marker_color=[CORAL if i == 0 else AMBER for i in range(len(pa))], name="nombre")
    fig.add_scatter(x=pa.lab, y=pa["cumul %"], yaxis="y2", mode="lines+markers", line=dict(color=GREEN),
                    name="cumul %")
    fig.update_layout(title="Pareto des non-conformités (en-cours et final)",
                      yaxis2=dict(overlaying="y", side="right", range=[0, 105], ticksuffix=" %"),
                      xaxis_tickangle=0, xaxis_tickfont_size=11)
    fig = style(fig, 380)
    fig.update_layout(legend_y=-0.32)
    a.plotly_chart(fig, width="stretch")
    p = kpi.p_chart()
    fig = go.Figure()
    fig.add_scatter(x=p.day, y=p.p.where(p.p > 0), mode="markers", name="taux de refus au test final",
                    line=dict(color=SLATE), marker=dict(color=[CORAL if h else SLATE for h in p["hors contrôle"]],
                                                         size=[11 if h else 6 for h in p["hors contrôle"]]))
    fig.add_scatter(x=p.day, y=p.LSC, mode="lines", name="limite de contrôle", line=dict(color=CORAL, dash="dash"))
    fig.update_layout(title="Carte p du test final : l'alerte du jour 25 (échelle log)", yaxis_tickformat=".1%",
                      yaxis_type="log", yaxis_tickvals=[0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])
    fig = style(fig, 380)
    fig.update_layout(legend_y=-0.12)
    b.plotly_chart(fig, width="stretch")
    a, b = st.columns([1, 1])
    nb = kpi.noise_by_day()
    fig = go.Figure()
    fig.add_scatter(x=nb.day, y=nb.maxi, name="maximum du jour", mode="lines", line=dict(color=AMBER))
    fig.add_scatter(x=nb.day, y=nb.moyenne, name="moyenne", mode="lines", line=dict(color=LEAF, width=3))
    fig.add_hline(y=82, line_color=CORAL, line_dash="dash", annotation_text="limite 82 dB(A)")
    fig.update_layout(title="Niveau sonore mesuré au test final", yaxis_title="dB(A)")
    a.plotly_chart(style(fig), width="stretch")
    with b:
        st.subheader("8D : bruit excessif au test final")
        d8 = query("SELECT d_step, owner, content FROM corrective_action ORDER BY ca_id")
        for _, r in d8.iterrows():
            st.markdown(f'<span class="tag">{r.d_step}</span> <b>{r.owner}</b> · {r.content}', unsafe_allow_html=True)
    st.subheader("Plans de contrôle")
    st.dataframe(query("SELECT plan_id, stage étape, item_id article, characteristic caractéristique, "
                       "COALESCE(CAST(lsl AS TEXT), '') LSL, COALESCE(CAST(usl AS TEXT), '') USL, unit unité, "
                       "sample_size échantillon FROM control_plan"), hide_index=True, width="stretch")


def page_stock():
    hero("Stock et réapprovisionnement", "Règles de point de commande, couverture des composants et calcul des "
         "besoins nets.")
    items = [i for i in md.ITEMS if i[2] in ("composant", "emballage")]
    label = {f"{i[0]} · {i[1]}": i[0] for i in items}
    sel = st.selectbox("Article", list(label), index=1)
    s = kpi.stock_item(label[sel])
    fig = go.Figure()
    fig.add_scatter(x=s.day, y=s["position (stock + en commande)"], name="position (stock + en commande)",
                    line=dict(color=AMBER, dash="dot", width=2))
    fig.add_scatter(x=s.day, y=s.stock, name="stock physique", fill="tozeroy", line=dict(color=LEAF, width=3),
                    fillcolor="rgba(62,155,110,.18)")
    fig.add_hline(y=s["point de commande"].iloc[0], line_color=SLATE, line_dash="dash",
                  annotation_text="point de commande")
    fig.add_hline(y=s["stock de sécurité"].iloc[0], line_color=CORAL, line_dash="dash",
                  annotation_text="stock de sécurité")
    fig.update_layout(title=f"Stock de {sel}", xaxis_title="jour", yaxis_title="pièces")
    st.plotly_chart(style(fig, 360), width="stretch")
    a, b = st.columns([1.1, 1])
    low = query("""SELECT i.name, MIN(CAST(s.stock AS REAL) / r.reorder_point) mini,
                          MAX(r.safety_stock * 1.0 / r.reorder_point) ss
                   FROM v_stock_jour s JOIN replenishment_rule r USING (item_id) JOIN item i USING (item_id)
                   WHERE s.day > 1 GROUP BY s.item_id ORDER BY mini""")
    fig = go.Figure(go.Bar(x=low.mini, y=low.name, orientation="h",
                           marker_color=[CORAL if m < ss else AMBER if m < 0.25 else LEAF
                                         for m, ss in zip(low.mini, low.ss, strict=True)]))
    fig.update_layout(title="Point bas du stock sur 40 jours (en % du point de commande)",
                      yaxis_autorange="reversed", xaxis_tickformat=".0%")
    a.plotly_chart(style(fig, 460, legend=False), width="stretch")
    with b:
        st.subheader("Règles de réapprovisionnement")
        st.dataframe(query("SELECT item_id article, reorder_point 'point de commande', order_qty 'quantité', "
                           "safety_stock 'stock de sécurité', home_loc emplacement FROM replenishment_rule"),
                     hide_index=True, height=400, width="stretch")


def page_donnees():
    hero("Données de base", "Articles, nomenclatures, gammes, emplacements et contrôles de cohérence avant mise en "
         "service.")
    rules = query("SELECT * FROM replenishment_rule").values.tolist()
    issues = checks.check(md.ITEMS, md.BOM, md.ROUTING, md.WORKCENTERS, md.SUPPLIERS, md.locations(),
                          md.CONTROL_PLANS, [tuple(r) for r in rules])
    c = st.columns(5)
    kpi_card(c[0], "Articles", len(md.ITEMS), f"{sum(i[3] == 'lot' for i in md.ITEMS)} suivis par lot")
    kpi_card(c[1], "Lignes de nomenclature", len(md.BOM), "2 produits, 4 sous-ensembles")
    kpi_card(c[2], "Opérations de gamme", len(md.ROUTING), "4 postes de travail")
    kpi_card(c[3], "Emplacements", len(md.locations()), "codes-barres normalisés")
    kpi_card(c[4], "Anomalies de données", len(issues), "contrôles de cohérence", "" if not issues else "bad")
    st.write("")
    a, b = st.columns([1.1, 1])
    pf = a.radio("Nomenclature", ["PF-M1", "PF-M1P"], horizontal=True)
    names = {i[0]: i[1] for i in md.ITEMS}
    ids, parents = [pf], [""]
    def walk(p, prefix):
        for par, comp, _q in md.BOM:
            if par == p:
                node = f"{prefix}/{comp}"
                ids.append(node)
                parents.append(prefix)
                walk(comp, node)
    walk(pf, pf)
    fig = go.Figure(go.Sunburst(ids=ids, parents=parents, labels=[names[i.split("/")[-1]] for i in ids],
                                insidetextorientation="radial", marker=dict(colors=["#DCEFE4"] + [PALETTE[k % 6]
                                                                                       for k in range(len(ids) - 1)])))
    fig.update_layout(title=f"Nomenclature éclatée : {names[pf]}")
    a.plotly_chart(style(fig, 440, legend=False), width="stretch")
    with b:
        st.subheader("Gamme")
        st.dataframe(pd.DataFrame([r for r in md.ROUTING if r[0] == pf], columns=["article", "séq.", "poste",
                                  "opération", "temps standard (s)", "point de contrôle"]).drop(columns="article"),
                     hide_index=True, width="stretch")
        st.subheader("Contrôles de cohérence")
        st.markdown("Fournisseur et coût de chaque article acheté · nomenclature et gamme de chaque article fabriqué · "
                    "absence de cycle · traçabilité des composants critiques · plan de contrôle à réception · format "
                    "des codes-barres · règle de réapprovisionnement et emplacement.")
        if issues:
            st.dataframe(pd.DataFrame([i.__dict__ for i in issues]), hide_index=True)
        else:
            st.success("Aucune anomalie : les données de base sont prêtes pour la mise en service.")
    st.subheader("Plan des emplacements de stock")
    locs = [loc for loc in md.locations() if loc[1] == "stock"]
    grid = pd.DataFrame([(loc[0][4], int(loc[0][5:7]), int(loc[0][-1]), loc[0]) for loc in locs],
                        columns=["allée", "baie", "niveau", "code"])
    rules_df = query("SELECT home_loc, item_id FROM replenishment_rule")
    grid = grid.merge(rules_df, left_on="code", right_on="home_loc", how="left")
    fig = go.Figure(go.Scatter(x=grid.allée + "-" + grid.baie.astype(str), y=grid.niveau, mode="markers+text",
                               marker=dict(symbol="square", size=46,
                                           color=[LEAF if pd.notna(v) else "#DDD5C6" for v in grid.item_id]),
                               text=grid.item_id.fillna(""), textfont=dict(color="white", size=10),
                               hovertext=grid.code))
    fig.update_layout(title="Allées A à C, baies 1 à 4, niveaux 1 à 3 : article affecté à chaque emplacement",
                      yaxis=dict(tickvals=[1, 2, 3], title="niveau"), xaxis_title="allée-baie")
    st.plotly_chart(style(fig, 300, legend=False), width="stretch")


def page_deploiement():
    hero("Plan de déploiement", "Quatre volets de l'ERP, six étapes chacun, validées par le responsable de "
         "production et la direction.")
    steps = ["Cartographie des flux et besoins", "Paramétrage et adaptations", "Données de base fiabilisées",
             "Tests avec les utilisateurs", "Formation et modes opératoires", "Mise en service accompagnée"]
    volets = {"Logistique": ["fait", "fait", "fait", "fait", "en cours", "à faire"],
              "Stockage": ["fait", "fait", "fait", "en cours", "à faire", "à faire"],
              "Production": ["fait", "fait", "fait", "fait", "fait", "en cours"],
              "Qualité": ["fait", "fait", "en cours", "à faire", "à faire", "à faire"]}
    color = {"fait": (LEAF, "white"), "en cours": (AMBER, "white"), "à faire": ("#ECE5D8", "#8B8270")}
    head = "".join(f'<div class="dh">{i + 1}. {t}</div>' for i, t in enumerate(steps))
    rows = ""
    for v, sl in volets.items():
        done = sum(x == "fait" for x in sl) + 0.5 * sum(x == "en cours" for x in sl)
        pct = round(100 * done / len(sl))
        cells = "".join(f'<div class="dc" style="background:{color[x][0]};color:{color[x][1]}">{x}</div>' for x in sl)
        rows += (f'<div class="dv"><b>{v}</b><div class="bar"><span style="width:{pct}%"></span></div>'
                 f'<small>{pct} %</small></div>{cells}')
    st.markdown(f"""<style>
      .dg {{ display:grid; grid-template-columns: 1.3fr repeat(6, 1fr); gap:8px; background:white;
             padding:22px; border-radius:16px; }}
      .dh {{ font-size:12.5px; font-weight:600; color:{GREEN}; padding:4px 2px 8px; line-height:1.3; }}
      .dv {{ display:flex; flex-direction:column; justify-content:center; gap:4px; color:{INK}; }}
      .dv small {{ color:#7A7468; }}
      .bar {{ height:6px; background:#ECE5D8; border-radius:9px; overflow:hidden; width:85%; }}
      .bar span {{ display:block; height:100%; background:{LEAF}; }}
      .dc {{ border-radius:10px; padding:16px 4px; text-align:center; font-size:13px; font-weight:600; }}
    </style><div class="dg"><div class="dh">Volet · avancement</div>{head}{rows}</div>""", unsafe_allow_html=True)
    st.caption("Exemple de suivi : l'état des étapes est illustratif.")
    st.markdown('<div class="note">Le détail des étapes, les décisions structurantes (codification des articles et '
                "des emplacements, règles de lot et de série, plans de contrôle) et les modes opératoires "
                "d'atelier sont décrits dans <code>docs/</code>.</div>", unsafe_allow_html=True)


pages = [st.Page(page_direction, title="Direction", icon="📈", default=True),
         st.Page(page_atelier, title="Atelier", icon="🛠️", url_path="atelier"),
         st.Page(page_tracabilite, title="Traçabilité", icon="🔎", url_path="tracabilite"),
         st.Page(page_qualite, title="Qualité", icon="✅", url_path="qualite"),
         st.Page(page_stock, title="Stock et réappro", icon="📦", url_path="stock"),
         st.Page(page_donnees, title="Données de base", icon="🗂️", url_path="donnees"),
         st.Page(page_deploiement, title="Déploiement", icon="🚀", url_path="deploiement")]
with st.sidebar:
    st.markdown("## 🏭 Usine M1")
    st.caption("Socle ERP · suivi de production · qualité · traçabilité")
nav = st.navigation(pages)
nav.run()
with st.sidebar:
    st.caption("Démonstrateur sur données simulées : produit, fournisseurs et clients fictifs.")
