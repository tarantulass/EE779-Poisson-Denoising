"""Results deck on the EE779.odp template: same canvas (10 x 5.625 in), Arial, black on white,
title at (0.5, 0.33), "k / N" footer and reference tag at the bottom.

Every number is read from the result logs: results/test.csv, results/test_bin3.csv (test images)
and results/tuned_params.json (tuning images), plus the paper's Table 1 for the replication slide.

    python3 build_odp_style.py RESULTS_DIR TEMPLATE.pptx OUT.pptx EXAMPLES_DIR CONVERGENCE_PNG
"""
import copy
import json
import sys

import numpy as np
import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt, Emu
from scipy.stats import wilcoxon

RES, TEMPLATE, OUT, EX, CONV = sys.argv[1:6]
PEAKS = [0.1, 0.2, 0.5, 1.0, 2.0, 4.0]
PL = ["0.1", "0.2", "0.5", "1", "2", "4"]
NAME = {
    "anscombe_bm3d": "Anscombe + BM3D", "anscombe_bm3d_algebraic": "Anscombe + BM3D, algebraic inverse",
    "p4ip_bm3d": "P4IP + BM3D", "spda": "SPDA",
    "A1_wavelet": "A1 wavelet, one threshold", "A1_subband": "A1 wavelet, per-level thresholds",
    "A2_wavelet_dict": "A2 wavelet-patch dictionary", "A2_pixel_dict": "A2 pixel dictionary",
    "A3_bm3d_wavelet": "A3 BM3D + wavelet (multiple priors)",
    "B_fista_swt": "B FISTA, redundant wavelet", "B_ista_swt": "B ISTA, redundant wavelet",
    "B_fista_dict": "B FISTA, learned dictionary", "B_ista_dict": "B ISTA, learned dictionary",
    "mean_filter": "Mean filter", "gaussian_filter": "Gaussian filter", "median_filter": "Median filter",
    "wiener_filter": "Wiener filter", "wavelet_threshold": "Wavelet thresholding", "nl_means": "Non-local means",
    "poisson_tv": "Poisson-TV",
}
ORDER = list(NAME)
HEAVY = ["p4ip_bm3d", "A2_wavelet_dict", "A2_pixel_dict", "A3_bm3d_wavelet"]

# ------------------------------------------------------------------ data from the logs
def load(f):
    d = pd.read_csv(f"{RES}/{f}")
    return d.groupby(["method", "image", "peak"], as_index=False).mean(numeric_only=True)

T0, T3 = load("test.csv"), load("test_bin3.csv")
TUNED = json.load(open(f"{RES}/tuned_params.json"))


def table_of(d, col="psnr"):
    return d.pivot_table(index="method", columns="peak", values=col, aggfunc="mean")


P0, P3 = table_of(T0), table_of(T3)
has0, has3 = set(P0.index), set(P3.index)


def tune_psnr(key, peak):
    v = TUNED.get(key, {}).get(str(float(peak)))
    return None if v is None else v["tune_psnr"]


def paired(d, m, ref="anscombe_bm3d"):
    out = []
    for p in PEAKS:
        a = d[(d.method == m) & (d.peak == p)].set_index("image").psnr
        r = d[(d.method == ref) & (d.peak == p)].set_index("image").psnr
        diff = (a - r).dropna()
        if len(diff) == 0:
            out.append(None); continue
        pv = wilcoxon(diff).pvalue if np.any(diff != 0) else 1.0
        out.append((diff.mean(), int((diff > 0).sum()), len(diff), pv))
    return out


def f2(v):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.2f}"


# ------------------------------------------------------------------ template handling
prs = Presentation(TEMPLATE)
LAYOUT = prs.slides[8].slide_layout
sldIdLst = prs.slides._sldIdLst
for sldId in list(sldIdLst):  # start from the template's masters and theme, without its slides
    prs.part.drop_rel(sldId.rId)
    sldIdLst.remove(sldId)
SLIDES = []
BLACK = RGBColor(0, 0, 0)


def new_slide(title, refs=""):
    s = prs.slides.add_slide(LAYOUT)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    if title:
        text(s, title, 0.5, 0.33, 9.0, 0.53, 23, bold=True)
    s._refs = refs
    SLIDES.append(s)
    return s


def text(s, content, x, y, w, h, size=15, bold=False, align=PP_ALIGN.LEFT, gap=0, anchor=MSO_ANCHOR.TOP):
    """content: a string, or a list of paragraphs; a paragraph is a string or a list of (text, bold) runs."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = content if isinstance(content, list) else [content]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if gap and i > 0:
            p.space_before = Pt(gap)
        runs = para if isinstance(para, list) else [(para, bold)]
        for t, b in runs:
            r = p.add_run()
            r.text = t
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = "Arial", Pt(size), b, BLACK
    return tb


def table(s, rows, x, y, w, col_w, size=11, row_h=0.26, header=True, right_from=1, bold_cells=()):
    nr, nc = len(rows), len(rows[0])
    gf = s.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr  # plain table like the template: no style, no banding, no borders
    for k in list(tblPr.attrib):
        del tblPr.attrib[k]
    for child in list(tblPr):
        tblPr.remove(child)
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i in range(nr):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            c = tbl.cell(i, j)
            v = rows[i][j]
            c.text = "" if v is None else str(v)
            c.margin_left = c.margin_right = Emu(68400)
            c.margin_top = c.margin_bottom = Emu(20000)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid(); c.fill.fore_color.rgb = RGBColor(255, 255, 255)
            tcPr = c._tc.get_or_add_tcPr()
            for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
                ln = etree.SubElement(tcPr, qn(tag)); etree.SubElement(ln, qn("a:noFill"))
            # border elements must precede the fill in tcPr
            fill = tcPr.find(qn("a:solidFill")); tcPr.remove(fill); tcPr.append(fill)
            for p in c.text_frame.paragraphs:
                p.alignment = PP_ALIGN.RIGHT if j >= right_from else PP_ALIGN.LEFT
                for r in p.runs:
                    r.font.name, r.font.size, r.font.color.rgb = "Arial", Pt(size), BLACK
                    r.font.bold = (header and i == 0) or (i, j) in bold_cells
    if header:  # one thin rule under the header row so long tables stay readable
        for j in range(nc):
            tcPr = tbl.cell(0, j)._tc.tcPr
            lnB = tcPr.find(qn("a:lnB")); tcPr.remove(lnB)
            lnB = etree.Element(qn("a:lnB"), w="9525")
            sf = etree.SubElement(lnB, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr"), val="000000")
            tcPr.insert(3, lnB)
    return tbl


COLORS = {"anscombe_bm3d": "000000", "p4ip_bm3d": "D62728", "spda": "FF7F0E", "A1_subband": "1F77B4",
          "A1_wavelet": "9EC5E8", "A2_wavelet_dict": "9467BD", "A2_pixel_dict": "C5B0D5", "A3_bm3d_wavelet": "8C564B",
          "B_fista_dict": "2CA02C", "B_fista_swt": "98DF8A", "gaussian_filter": "7F7F7F", "poisson_tv": "BCBD22",
          "mean_filter": "C7C7C7", "nl_means": "17BECF", "wavelet_threshold": "E377C2", "wiener_filter": "8C8C8C",
          "anscombe_bm3d_algebraic": "7F7F7F"}


def style_chart(ch, ytitle):
    ch.font.name, ch.font.size = "Arial", Pt(10)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.RIGHT
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(9)
    va, ca = ch.value_axis, ch.category_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xD9, 0xD9, 0xD9)
    va.has_title = True; va.axis_title.text_frame.text = ytitle
    ca.has_title = True; ca.axis_title.text_frame.text = "peak photons"
    for ax in (va, ca):
        for p in ax.axis_title.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.name = Pt(10), False, "Arial"
        ax.tick_labels.font.size = Pt(10)


def line_chart(s, pt, methods, x, y, w, h, ymin, ymax):
    methods = [m for m in methods if m in pt.index and not pt.loc[m].isna().any()]
    cd = CategoryChartData(); cd.categories = PL
    for m in methods:
        cd.add_series(NAME[m], [float(pt.loc[m, p]) for p in PEAKS])
    ch = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    style_chart(ch, "PSNR (dB)")
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = ymin, ymax
    for ser, m in zip(ch.plots[0].series, methods):
        ser.format.line.color.rgb = RGBColor.from_string(COLORS.get(m, "7F7F7F"))
        ser.format.line.width = Pt(2 if m in ("anscombe_bm3d", "p4ip_bm3d") else 1.5)
        ser.smooth = False
        ser.marker.style = XL_MARKER_STYLE.CIRCLE; ser.marker.size = 5
        ser.marker.format.fill.solid(); ser.marker.format.fill.fore_color.rgb = RGBColor.from_string(COLORS.get(m, "7F7F7F"))
        ser.marker.format.line.color.rgb = RGBColor.from_string(COLORS.get(m, "7F7F7F"))
    return ch


def bar_chart(s, cats, series, x, y, w, h, ytitle, colors, fmt="0.0", labels=True):
    cd = CategoryChartData(); cd.categories = cats
    for n, v in series:
        cd.add_series(n, v)
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    style_chart(ch, ytitle)
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    for ser, c in zip(ch.plots[0].series, colors):
        ser.format.fill.solid(); ser.format.fill.fore_color.rgb = RGBColor.from_string(c)
    if labels:
        pl = ch.plots[0]; pl.has_data_labels = True
        pl.data_labels.number_format, pl.data_labels.number_format_is_linked = fmt, False
        pl.data_labels.font.size = Pt(8)
    return ch


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


PAPER_REF = "[1]"

# ------------------------------------------------------------------ 1. title (layout of the template's slide 1)
s = new_slide(None, "")
text(s, "EE779 Project", 0.38, 0.27, 8.87, 0.35, 14, bold=True)
text(s, "Poisson denoising", 0.38, 0.69, 9.0, 0.53, 21, bold=True)
text(s, "Results: baselines, replication and proposed directions", 0.35, 1.28, 8.87, 0.45, 17)
text(s, [[("Members", True)], "1.  Jeet Kattirsitti", "2.  Rajwardhan Toraskar"], 0.38, 1.91, 4.0, 0.85, 14)
for i, t in enumerate(["Setup and replication of the P4IP paper",
                       "Baselines and the proposed directions A and B",
                       "Binning, statistical tests and conclusions"]):
    text(s, t, 0.5, 3.17 + 0.5 * i, 9.0, 0.48, 15)
notes(s, "Results of the experiments proposed in the EE779 deck. Every number on the following slides is read from the "
         "result logs of our code (results/test.csv, results/test_bin3.csv, results/tuned_params.json).")

# ------------------------------------------------------------------ 2. setup
s = new_slide("Experimental setup")
text(s, [
    "x = p s,   max(s) = 1,   yᵢ ∼ Poisson(xᵢ),   p ∈ {0.1, 0.2, 0.5, 1, 2, 4}",
    "Test: 8 images, one noise draw per image and peak. The seed depends only on (image, peak), so every method sees the same counts.",
    "Tuning: every free parameter is chosen per peak on 4 separate tuning images. 400 training images for the A2 dictionaries.",
    "Binning: 3×3 block sums, denoise, interpolate back. Tuned and reported separately.",
    "Measured: PSNR = 10 log₁₀(p² / MSE) as in the papers, SSIM, runtime, sparsity, convergence residuals.",
    "Comparison: paired Wilcoxon signed-rank test against Anscombe + BM3D over the 8 test images.",
], 0.5, 1.13, 9.0, 3.9, 14, gap=9)

# ------------------------------------------------------------------ 3. methods
s = new_slide("Methods implemented")
table(s, [["Group", "Method", "Slide", "Module"],
          ["Conventional", "Mean, Gaussian, median, Wiener, wavelet threshold, NL-means, Poisson-TV", "3", "baselines/conventional.py"],
          ["Baselines", "Anscombe + BM3D, exact and algebraic inverse", "4, 5", "baselines/anscombe_bm3d.py"],
          ["", "P4IP + BM3D (Plug-and-Play ADMM, 70 iterations)", "7, 8", "baselines/p4ip.py"],
          ["", "SPDA (exp(Dα), shared supports, simplified)", "6", "baselines/spda.py"],
          ["Direction A", "A1 wavelet shrinkage prior, one or per-level thresholds", "10", "direction_a/a1_wavelet.py"],
          ["", "A2 learned wavelet-patch vs pixel dictionary, 256 atoms each", "10", "direction_a/a2_dictionary.py"],
          ["", "A3 BM3D + wavelet consensus (multiple priors)", "10", "direction_a/a3_consensus.py"],
          ["Direction B", "ISTA vs FISTA on ½‖Dα − z‖² + λ‖α‖₁, D = redundant wavelet or learned dictionary", "11", "direction_b/ista_fista.py"]],
      0.5, 1.13, 9.0, [1.2, 4.75, 0.6, 2.45], size=10.5, row_h=0.36, right_from=99)
text(s, "All modules are in experiments/ of the repository.", 0.5, 4.73, 9.0, 0.33, 11)

# ------------------------------------------------------------------ 4. replication
s = new_slide("Replication of the P4IP paper, Table 1", PAPER_REF)
rows = [["Method", "Source", "peak 0.1", "peak 0.2", "peak 1"]]
paper = {"anscombe_bm3d": [16.59, 18.43, 21.73], "spda": [15.48, 18.57, 23.61], "p4ip_bm3d": [17.85, 19.33, 22.88]}
for m in ("anscombe_bm3d", "spda", "p4ip_bm3d"):
    rows.append([NAME[m], "paper (8 images)", *[f"{v:.2f}" for v in paper[m]]])
    rows.append(["", "ours, 8 test images",
                 *[f2(P0.loc[m, p]) if m in has0 else "running" for p in (0.1, 0.2, 1.0)]])
    rows.append(["", "ours, 4 tuning images", *[f2(tune_psnr(m, p)) for p in (0.1, 0.2, 1.0)]])
table(s, rows, 0.5, 1.05, 9.0, [2.3, 2.5, 1.4, 1.4, 1.4], size=10, row_h=0.25, right_from=2)
lead = [p for p in (0.1, 0.2, 1.0) if tune_psnr("p4ip_bm3d", p) > tune_psnr("anscombe_bm3d", p)]
spda_lead = [p for p in (0.1, 0.2, 1.0) if tune_psnr("spda", p) > tune_psnr("p4ip_bm3d", p)]
text(s, "Same peaks and PSNR definition as the paper; different images and our own implementations. On our tuning images "
        f"P4IP + BM3D beats Anscombe + BM3D at peaks {', '.join(f'{p:g}' for p in lead)} (test images: {', '.join(f'{p:g}' for p in (0.1, 0.2, 1.0) if P0.loc['p4ip_bm3d', p] > P0.loc['anscombe_bm3d', p])}), as in the paper; "
        f"SPDA beats P4IP + BM3D at peak {', '.join(f'{p:g}' for p in spda_lead) or 'none'}.",
     0.5, 4.2, 9.0, 0.55, 11)
text(s, "Source: Rond, Giryes, Elad, arXiv:1511.02500 v1, Table 1 (no binning). Tuning-image values: results/tuned_params.json.",
     0.5, 4.73, 9.0, 0.33, 9)

# ------------------------------------------------------------------ 4b. per-image replication on the shared images
s = new_slide("Replication on the images shared with the paper", PAPER_REF)
PAPER_IMG = {  # Rond, Giryes, Elad, arXiv:1511.02500 v1, Table 1 (no binning), peaks 0.1 ... 4
    ("cameraman", "anscombe_bm3d"): [15.66, 17.35, 18.83, 20.37, 22.13, 23.94],
    ("cameraman", "p4ip_bm3d"): [16.88, 17.82, 19.27, 20.54, 21.87, 23.29],
    ("house", "anscombe_bm3d"): [16.28, 18.37, 20.27, 22.35, 24.18, 26.04],
    ("house", "p4ip_bm3d"): [18.30, 19.48, 20.93, 22.67, 24.65, 26.33],
    ("peppers", "anscombe_bm3d"): [15.61, 17.10, 18.49, 19.89, 21.97, 24.07],
    ("peppers", "p4ip_bm3d"): [16.28, 17.31, 18.86, 20.07, 21.33, 23.88],
}
rows = [["Paper / ours (dB)", *[f"peak {p}" for p in PL]]]
diffs = {"anscombe_bm3d": [], "p4ip_bm3d": []}
for (im, m), pv in PAPER_IMG.items():
    o = T0[(T0.image == im) & (T0.method == m)].set_index("peak").psnr
    short = "Anscombe + BM3D" if m == "anscombe_bm3d" else "P4IP + BM3D"
    rows.append([f"{im.capitalize()}, {short}", *[f"{v:.2f} / {f2(o.get(p))}" for p, v in zip(PEAKS, pv)]])
    diffs[m].append([o.get(p) - v for p, v in zip(PEAKS, pv)])
table(s, rows, 0.5, 1.05, 9.0, [2.7] + [1.05] * 6, size=10, row_h=0.3)
dm = {m: np.nanmean(np.array(v), axis=0) for m, v in diffs.items()}
text(s, [f"Ours minus paper, mean over the 3 images: P4IP + BM3D {', '.join(f'{x:+.2f}' for x in dm['p4ip_bm3d'])} dB; "
         f"Anscombe + BM3D {', '.join(f'{x:+.2f}' for x in dm['anscombe_bm3d'])} dB (peaks 0.1 to 4).",
         "From peak 0.2 up our P4IP + BM3D is within about 0.3 dB of the paper on the same images. The largest gaps are at peak 0.1, "
         "where counts are fewest; both studies use their own noise draws, which cannot be matched."],
     0.5, 3.45, 9.0, 1.3, 11, gap=6)
text(s, "Cameraman, House and Peppers are in both test sets. Paper: Table 1 of arXiv:1511.02500 v1; ours: results/test.csv.", 0.5, 4.95, 9.0, 0.25, 9)

# ------------------------------------------------------------------ 5. main chart
s = new_slide("PSNR vs peak on the test images, no binning")
line_chart(s, P0, ["anscombe_bm3d", "p4ip_bm3d", "spda", "A1_subband", "A3_bm3d_wavelet", "A2_wavelet_dict",
                   "B_fista_dict", "gaussian_filter", "poisson_tv"], 0.5, 1.05, 9.0, 3.7, 12, 24)
text(s, "Mean over 8 test images. P4IP + BM3D beats Anscombe + BM3D up to peak 1; strong averaging (SPDA, Gaussian filter) "
        "is competitive at the lowest peaks; Anscombe + BM3D is best at peaks 2 and 4.", 0.5, 4.8, 9.0, 0.45, 11)


# ------------------------------------------------------------------ 6/7. full tables
def full_table(pt, title, note, tune_key_suffix=""):
    s = new_slide(title)
    ms = [m for m in ORDER if m in pt.index]
    best = {p: pt.loc[ms, p].max(skipna=True) for p in PEAKS}
    rows = [["Method", *[f"peak {p}" for p in PL]]]
    bold = []
    for i, m in enumerate(ms, start=1):
        rows.append([NAME[m] + (" (partial)" if pt.loc[m].isna().any() else ""), *[f2(pt.loc[m, p]) for p in PEAKS]])
        bold += [(i, j + 1) for j, p in enumerate(PEAKS) if pt.loc[m, p] == best[p]]
    for m in ORDER:
        if m not in pt.index:
            rows.append([NAME[m] + " (not run)", *["–"] * 6])
    table(s, rows, 0.5, 0.98, 9.0, [3.3] + [0.95] * 6, size=8.5, row_h=0.19, bold_cells=bold)
    text(s, note, 0.5, 5.02, 9.0, 0.22, 9)
    return s


full_table(P0, "Mean PSNR (dB), test images, no binning", "Bold: best per peak. Source: results/test.csv.")
full_table(P3, "Mean PSNR (dB), test images, 3×3 binning", "Bold: best per peak. Source: results/test_bin3.csv.")

# ------------------------------------------------------------------ 8. P4IP-type methods on tuning images (unbinned)
s = new_slide("P4IP-type methods, tuning images, no binning")
rows = [["Method", *[f"peak {p}" for p in PL]]]
TM = ["anscombe_bm3d", "spda", "A1_subband", "p4ip_bm3d", "A3_bm3d_wavelet", "A2_wavelet_dict", "A2_pixel_dict"]
vals = {m: [tune_psnr(m, p) for p in PEAKS] for m in TM}
best = [max(v[i] for v in vals.values() if v[i] is not None) for i in range(6)]
bold = [(i, j + 1) for i, m in enumerate(TM, 1) for j in range(6) if vals[m][j] == best[j]]
for m in TM:
    rows.append([NAME[m], *[f2(v) for v in vals[m]]])
table(s, rows, 0.5, 1.13, 9.0, [3.3] + [0.95] * 6, size=10.5, row_h=0.28, bold_cells=bold)
text(s, ["Mean PSNR over the 4 tuning images at the tuned parameters (results/tuned_params.json). "
         "Test-image results without binning: P4IP + BM3D complete, A3 " + ("complete" if "A3_bm3d_wavelet" in has0 and not P0.loc["A3_bm3d_wavelet"].isna().any() else "partial") + ", A2 not run (too slow; binned test results are on the binned table).",
         f"P4IP + BM3D beats Anscombe + BM3D at peaks {', '.join(PL[i] for i in range(6) if vals['p4ip_bm3d'][i] > vals['anscombe_bm3d'][i])}. "
         f"A3 beats P4IP + BM3D at peaks {', '.join(PL[i] for i in range(6) if round(vals['A3_bm3d_wavelet'][i], 2) > round(vals['p4ip_bm3d'][i], 2))}. Bold: best per peak."],
     0.5, 3.45, 9.0, 1.3, 12, gap=8)

# ------------------------------------------------------------------ 9. multiple priors
s = new_slide("Multiple priors: BM3D + wavelet consensus (A3)")
text(s, "Each ADMM iteration denoises with BM3D and with wavelet shrinkage; the prior step averages the two (ρ_eff = 2ρ).",
     0.5, 1.05, 9.0, 0.45, 13)
rows = [["", *[f"peak {p}" for p in PL]]]
rows.append(["P4IP + BM3D, tuning", *[f2(tune_psnr("p4ip_bm3d", p)) for p in PEAKS]])
rows.append(["A3 BM3D + wavelet, tuning", *[f2(tune_psnr("A3_bm3d_wavelet", p)) for p in PEAKS]])
rows.append(["Difference", *[f"{tune_psnr('A3_bm3d_wavelet', p) - tune_psnr('p4ip_bm3d', p):+.2f}" for p in PEAKS]])
if "A3_bm3d_wavelet" in has0 and "p4ip_bm3d" in has0:
    rows.append(["P4IP + BM3D, test", *[f2(P0.loc["p4ip_bm3d", p]) for p in PEAKS]])
    rows.append(["A3 BM3D + wavelet, test", *[f2(P0.loc["A3_bm3d_wavelet", p]) for p in PEAKS]])
if "A3_bm3d_wavelet" in has3 and "p4ip_bm3d" in has3:
    rows.append(["P4IP + BM3D, test, 3×3 binned", *[f2(P3.loc["p4ip_bm3d", p]) for p in PEAKS]])
    rows.append(["A3 BM3D + wavelet, test, 3×3 binned", *[f2(P3.loc["A3_bm3d_wavelet", p]) for p in PEAKS]])
table(s, rows, 0.5, 1.55, 9.0, [3.3] + [0.95] * 6, size=10, row_h=0.25, bold_cells=[(3, 1), (3, 2)])
d01 = tune_psnr("A3_bm3d_wavelet", 0.1) - tune_psnr("p4ip_bm3d", 0.1)
d01t = P0.loc["A3_bm3d_wavelet", 0.1] - P0.loc["p4ip_bm3d", 0.1] if "A3_bm3d_wavelet" in has0 else float("nan")
text(s, [f"Without binning the wavelet prior adds {d01:.2f} dB at peak 0.1 on the tuning images ({d01t:+.2f} dB on the test images) and {tune_psnr('A3_bm3d_wavelet', 0.2) - tune_psnr('p4ip_bm3d', 0.2):.2f} dB at 0.2; "
         "from peak 0.5 up the tuned wavelet weight is the smallest tried and A3 equals P4IP + BM3D.",
         "With binning A3 is worse at every peak. Both binned runs used an older P4IP grid whose best ρ₀ lay at the grid edge, so the binned P4IP-type numbers are a lower bound."],
     0.5, 3.75, 9.0, 1.2, 11, gap=6)

# ------------------------------------------------------------------ 10. direction A overview
s = new_slide("Direction A: changing the P4IP prior")
line_chart(s, P3, ["anscombe_bm3d", "p4ip_bm3d", "A1_wavelet", "A1_subband", "A2_wavelet_dict", "A2_pixel_dict",
                   "A3_bm3d_wavelet"], 0.5, 1.05, 5.6, 3.6, 14, 23)
a1 = [P0.loc["A1_subband", p] - P0.loc["A1_wavelet", p] for p in PEAKS]
a2 = [P3.loc["A2_wavelet_dict", p] - P3.loc["A2_pixel_dict", p] for p in PEAKS] if "A2_wavelet_dict" in has3 else None
lines = [f"A1: per-level thresholds gain {min(a1):.2f} to {max(a1):.2f} dB over one threshold (test, no binning).",
         f"A1 vs Anscombe + BM3D: {P0.loc['A1_subband', 0.1] - P0.loc['anscombe_bm3d', 0.1]:+.2f} dB at peak 0.1, "
         f"{P0.loc['A1_subband', 4.0] - P0.loc['anscombe_bm3d', 4.0]:+.2f} dB at peak 4."]
if a2:
    lines.append(f"A2: wavelet-patch minus pixel dictionary {min(a2):+.2f} to {max(a2):+.2f} dB (test, binned). "
                 "The wavelet structure does not help.")
lines.append("A3: see the previous slide.")
text(s, lines, 6.3, 1.1, 3.2, 3.7, 11.5, gap=8)
text(s, "Chart: test images with 3×3 binning, the only setting where all Direction A runs have finished.", 0.5, 4.75, 9.0, 0.3, 9)

# ------------------------------------------------------------------ 11. direction B
s = new_slide("Direction B: ISTA vs FISTA on the same objective")
it0, it3, tm3 = table_of(T0, "iterations"), table_of(T3, "iterations"), table_of(T3, "time")
rows = [["3×3 binned", "PSNR ISTA", "PSNR FISTA", "iter. ISTA", "iter. FISTA", "s ISTA", "s FISTA"]]
for fr, lab in (("swt", "wavelet"), ("dict", "dictionary")):
    for p in (0.5, 1.0, 4.0):
        rows.append([f"{lab}, peak {p:g}", f2(P3.loc[f"B_ista_{fr}", p]), f2(P3.loc[f"B_fista_{fr}", p]),
                     f"{it3.loc[f'B_ista_{fr}', p]:.0f}", f"{it3.loc[f'B_fista_{fr}', p]:.0f}",
                     f"{tm3.loc[f'B_ista_{fr}', p]:.1f}", f"{tm3.loc[f'B_fista_{fr}', p]:.1f}"])
table(s, rows, 0.5, 1.1, 5.5, [1.5, 0.65, 0.7, 0.65, 0.7, 0.6, 0.7], size=9.5, row_h=0.27)
s.shapes.add_picture(CONV, Inches(6.15), Inches(1.1), Inches(3.35), Inches(2.93))
ratio = [it3.loc[f"B_ista_{fr}", p] / it3.loc[f"B_fista_{fr}", p] for fr in ("swt", "dict") for p in PEAKS
         if it3.loc[f"B_ista_{fr}", p] > 5]
zero = [p for p in PEAKS if it0.loc["B_fista_dict", p] <= 1 and it0.loc["B_fista_swt", p] <= 1]
text(s, [f"Same λ, start α⁰ = 0 and stopping rule |ΔF| ≤ 10⁻⁷F: the same PSNR; FISTA needs {min(ratio):.1f} to {max(ratio):.1f}× fewer iterations (ISTA often stops at the 2000-iteration cap, so these are lower bounds).",
         f"Without binning the tuned λ sets every detail coefficient to zero at peaks {', '.join(f'{p:g}' for p in zero)}: "
         "the estimate is the smooth coarse part of the Anscombe image."],
     0.5, 3.15, 5.5, 1.6, 11, gap=8)
text(s, "Right: (F_k − F*)/F*, cameraman, 3×3 binned; F* from 5000 FISTA iterations. Iteration cap 2000.", 0.5, 4.83, 9.0, 0.25, 9)

# ------------------------------------------------------------------ 12. inverse
s = new_slide("Exact vs algebraic inverse Anscombe")
bar_chart(s, PL, [("exact unbiased inverse", [float(P0.loc["anscombe_bm3d", p]) for p in PEAKS]),
                  ("algebraic inverse z²/4 − 3/8", [float(P0.loc["anscombe_bm3d_algebraic", p]) for p in PEAKS])],
          0.5, 1.05, 6.0, 3.8, "PSNR (dB)", ["1F77B4", "BFBFBF"])
gap = [P0.loc["anscombe_bm3d", p] - P0.loc["anscombe_bm3d_algebraic", p] for p in PEAKS]
text(s, [f"Same BM3D output, only the inverse changes: the exact inverse gains {min(gap):.1f} to {max(gap):.1f} dB.",
         f"The gap is largest at peak {PL[int(np.argmax(gap))]} and smallest at peak {PL[int(np.argmin(gap))]}.",
         "All Anscombe-based methods in this study use the exact inverse."], 6.7, 1.2, 2.8, 3.6, 12, gap=8)

# ------------------------------------------------------------------ 13. conventional
s = new_slide("Conventional methods")
line_chart(s, P0, ["anscombe_bm3d", "gaussian_filter", "mean_filter", "nl_means", "poisson_tv", "wavelet_threshold",
                   "wiener_filter"], 0.5, 1.05, 6.2, 3.7, 10, 24)
text(s, [f"Gaussian filter on the Anscombe image: {P0.loc['gaussian_filter', 0.1]:.2f} dB at peak 0.1, above Anscombe + BM3D ({P0.loc['anscombe_bm3d', 0.1]:.2f}).",
         f"Poisson-TV is the best conventional method at peak 2 ({P0.loc['poisson_tv', 2.0]:.2f} dB).",
         f"Median filter: {P0.loc['median_filter', 0.1]:.2f} dB at peak 0.1 (not plotted); most counts are 0."],
     6.9, 1.2, 2.6, 3.6, 11.5, gap=8)

# ------------------------------------------------------------------ 14. binning effect
s = new_slide("Effect of 3×3 binning")
BM = [m for m in ["anscombe_bm3d", "p4ip_bm3d", "spda", "A1_subband", "B_fista_dict", "nl_means", "poisson_tv"]
      if m in has0 and m in has3]
rows = [["PSNR binned − unbinned (dB)", *[f"peak {p}" for p in PL]]]
for m in BM:
    rows.append([NAME[m], *[f"{P3.loc[m, p] - P0.loc[m, p]:+.2f}" for p in PEAKS]])
table(s, rows, 0.5, 1.13, 9.0, [3.3] + [0.95] * 6, size=10.5, row_h=0.28)
text(s, [f"Binning helps at low counts: Anscombe + BM3D {P0.loc['anscombe_bm3d', 0.1]:.2f} → {P3.loc['anscombe_bm3d', 0.1]:.2f} dB at peak 0.1.",
         f"It costs resolution at high counts: {P0.loc['anscombe_bm3d', 4.0]:.2f} → {P3.loc['anscombe_bm3d', 4.0]:.2f} dB at peak 4.",
         "Best binned methods per peak are in bold on the binned PSNR table."], 0.5, 3.6, 9.0, 1.2, 12, gap=8)

# ------------------------------------------------------------------ 15/16. paired tests
def paired_slide(d, title, src, methods):
    s = new_slide(title)
    rows = [["Method minus Anscombe + BM3D (dB)", *[f"peak {p}" for p in PL]]]
    bold = []
    for i, m in enumerate([m for m in methods if m in set(d.method)], 1):
        r = [NAME[m]]
        for j, v in enumerate(paired(d, m)):
            if v is None:
                r.append("–"); continue
            mean, w, n, pv = v
            r.append(f"{mean:+.2f}{'*' if pv < 0.05 else ''}  ({w}/{n})")
            if pv < 0.05:
                bold.append((i, j + 1))
        rows.append(r)
    table(s, rows, 0.5, 1.13, 9.0, [2.88] + [1.02] * 6, size=9.5, row_h=0.27, bold_cells=bold)
    text(s, f"Mean paired difference over the 8 test images, (images better / 8). * and bold: Wilcoxon signed-rank p < 0.05 "
            f"(with 8 images the smallest possible p is 0.0078). Source: {src}.", 0.5, 4.75, 9.0, 0.4, 9)


PM = ["p4ip_bm3d", "spda", "A1_wavelet", "A1_subband", "A2_wavelet_dict", "A2_pixel_dict", "A3_bm3d_wavelet",
      "B_fista_swt", "B_fista_dict", "gaussian_filter", "nl_means", "poisson_tv"]
paired_slide(T0, "Paired comparison with Anscombe + BM3D, no binning", "results/test.csv", PM)
paired_slide(T3, "Paired comparison with Anscombe + BM3D, 3×3 binning", "results/test_bin3.csv", PM)

# ------------------------------------------------------------------ 17. SSIM and runtime
s = new_slide("SSIM and runtime")
S0, R0, R3 = table_of(T0, "ssim"), table_of(T0, "time"), table_of(T3, "time")
SR = ["anscombe_bm3d", "p4ip_bm3d", "spda", "A1_subband", "A2_wavelet_dict", "A3_bm3d_wavelet", "B_fista_dict",
      "B_ista_dict", "gaussian_filter", "poisson_tv"]
rows = [["Method", "SSIM 0.1", "SSIM 1", "SSIM 4", "s/image, peak 1", "s/image, binned"]]
for m in SR:
    rows.append([NAME[m], *[f"{S0.loc[m, p]:.3f}" if m in has0 else "–" for p in (0.1, 1.0, 4.0)],
                 f"{R0.loc[m, 1.0]:.1f}" if m in has0 else "–", f"{R3.loc[m, 1.0]:.1f}" if m in has3 else "–"])
table(s, rows, 0.5, 1.13, 9.0, [3.4, 0.95, 0.95, 0.95, 1.35, 1.4], size=10, row_h=0.27)
text(s, "SSIM on the test images without binning. Runtimes: a 2-core cloud machine for unbinned runs and a 12-core laptop for "
        "the binned P4IP-type runs, one image per core, so they are comparable within a column only.", 0.5, 4.3, 9.0, 0.6, 10)

# ------------------------------------------------------------------ 18. example
s = new_slide("Example: cameraman, peak 1, no binning")
info = json.load(open(f"{EX}/info.json"))
tiles = [("clean", "Clean"), ("noisy", "Noisy counts"), ("anscombe_bm3d", None), ("spda", None),
         ("poisson_tv", None), ("A1_subband", None), ("B_fista_dict", None), ("anscombe_bm3d_algebraic", None)]
for i, (k, lab) in enumerate(tiles):
    x, y = 0.5 + (i % 4) * 2.3, 1.0 + (i // 4) * 2.1
    s.shapes.add_picture(f"{EX}/{k}.png", Inches(x + 0.15), Inches(y), Inches(1.7), Inches(1.7))
    cap = (lab or NAME[k]) + (f", {info[k]:.2f} dB" if k in info else "")
    text(s, cap, x - 0.05, y + 1.72, 2.2, 0.3, 9, align=PP_ALIGN.CENTER)

# ------------------------------------------------------------------ 19. conclusions
s = new_slide("Conclusions")
text(s, [
    f"The exact unbiased inverse matters: {min(gap):.1f} to {max(gap):.1f} dB over the algebraic inverse.",
    f"Replication: on the test images P4IP + BM3D beats Anscombe + BM3D at peaks {', '.join(f'{p:g}' for p in PEAKS if P0.loc['p4ip_bm3d', p] > P0.loc['anscombe_bm3d', p])} "
    f"(+{P0.loc['p4ip_bm3d', 0.1] - P0.loc['anscombe_bm3d', 0.1]:.2f} dB at peak 0.1), as the paper reports; Anscombe + BM3D is better at the highest peaks.",
    f"Multiple priors: BM3D + wavelet improves P4IP + BM3D at peak 0.1 by {d01:.2f} dB (tuning) and {d01t:+.2f} dB (test); no gain from peak 0.5 up.",
    f"A1: per-level wavelet thresholds add up to {max(a1):.1f} dB; the wavelet prior alone stays below BM3D above peak 0.5.",
    "A2: the wavelet-patch dictionary is not better than the pixel dictionary.",
    f"Direction B: FISTA reaches the ISTA solution in {min(ratio):.1f} to {max(ratio):.1f}× fewer iterations; without binning the tuned problem is trivial.",
    "No method wins at every peak: SPDA and smooth estimators lead at the lowest counts, BM3D-based methods above.",
], 0.5, 1.13, 9.0, 3.9, 13, gap=7)

# ------------------------------------------------------------------ 20. limitations and reproduction
s = new_slide("Limitations and reproduction")
text(s, [
    "One noise draw per image; 8 test images, so a paired test can reach at best p = 0.0078.",
    "SPDA is simplified (fixed sparsity, k-means groups, 3 rounds). Our Anscombe + BM3D is below the paper's numbers.",
    "Some tuned parameters lie at the edge of their grid (flagged in the tuning log), mainly for the binned P4IP-type runs and A2. A2 without binning was tuned but not run on the test images (about 25 min per image).",
    [("Reproduce: ", True), ("python -m experiments.tune / evaluate --methods all [--bin 3]; python -m experiments.evaluate --summary", False)],
    [("AI use: ", True), ("code, README and this deck were written with Claude (Anthropic) following our proposal deck; every number is read from the result logs.", False)],
], 0.5, 1.13, 9.0, 3.9, 13, gap=9)

# ------------------------------------------------------------------ footers like the template
N = len(SLIDES)
for i, s in enumerate(SLIDES, 1):
    text(s, f"{i} / {N}", 0.5, 5.3, 2.34, 0.18, 9)
    if s._refs:
        text(s, s._refs, 8.52, 5.3, 0.98, 0.18, 9, align=PP_ALIGN.RIGHT)
prs.save(OUT)
print("wrote", OUT, N, "slides")
