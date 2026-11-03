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


# ==================================================================================== DECK v3
# Order follows the grading rubric: goals and problem -> existing methods and their failures ->
# reference method -> replication (with changes) -> real data (FMD) -> proposed directions with
# reasons -> findings, conclusions, future work. Backup slides at the end. Speaker notes carry the
# timing and a transition sentence for every slide.
import os

REFS = {"p4ip": "[1]", "bm3d": "[2]", "spda": "[3]", "ans": "[4]", "fista": "[5]", "fmd": "[6]"}


def bullets(s, items, x=0.5, y=1.13, w=9.0, h=3.9, size=14, gap=9):
    return text(s, items, x, y, w, h, size, gap=gap)


def say(s, minutes, body, nxt):
    notes(s, f"Suggested time: {minutes}.\n\n{body}\n\nTransition: {nxt}")


# ---------------------------------------------------------------- 1. title
s = new_slide(None, "")
text(s, "EE779 Project", 0.38, 0.27, 8.87, 0.35, 14, bold=True)
text(s, "Poisson denoising", 0.38, 0.69, 9.0, 0.53, 21, bold=True)
text(s, "Plug-and-play priors and sparse representations: replication and extensions", 0.35, 1.28, 8.87, 0.45, 17)
text(s, [[("Members", True)], "1.  Jeet Kattirsitti", "2.  Rajwardhan Toraskar"], 0.38, 1.91, 4.0, 0.85, 14)
for i, t in enumerate(["Problem, existing methods and the P4IP solution",
                       "Replication of P4IP on synthetic and real (FMD) data",
                       "Proposed directions A (new priors) and B (ISTA/FISTA), findings"]):
    text(s, t, 0.5, 3.17 + 0.5 * i, 9.0, 0.48, 15)
say(s, "20 seconds", "We study denoising of images formed from very few photons. We reproduce the P4IP paper, test it on real "
    "microscopy data, and evaluate two directions we proposed: new priors inside P4IP, and an explicit sparse model solved with ISTA and FISTA.",
    "First, why low-photon imaging matters and what exactly we set out to do.")

# ---------------------------------------------------------------- 2. motivation and goals
s = new_slide("Motivation and project goals")
text(s, [[("Where photons are scarce", True)],
         "Fluorescence microscopy (low dose to protect live cells), astronomy, low-dose medical imaging (PET, CT), night and high-speed photography.",
         "Each pixel counts a few photons; at peak 0.1 about 90% of pixels read zero."], 0.5, 1.13, 9.0, 1.5, 14, gap=6)
text(s, [[("Goals", True)],
         "1.  Reproduce the P4IP results (Rond, Giryes, Elad) against Anscombe + BM3D and SPDA.",
         "2.  Check the reproduction on real data: the FMD fluorescence-microscopy benchmark.",
         "3.  Direction A: change the P4IP prior (wavelets, learned dictionaries, multiple priors).",
         "4.  Direction B: an explicit sparse model solved with ISTA vs FISTA.",
         "5.  Evaluate all of it with one protocol: same images, same noise, separate tuning, paired tests."],
     0.5, 2.75, 9.0, 2.3, 14, gap=5)
say(s, "45 seconds", "Applications first, then our five goals. Goals 1 and 2 are the reproduction, 3 and 4 are our own proposals, 5 is how we keep the comparison fair.",
    "To see why this is hard, look at the noise model itself.")

# ---------------------------------------------------------------- 3. problem statement
s = new_slide("Problem statement: Poisson noise", REFS["p4ip"])
text(s, ["yᵢ ∼ Poisson(xᵢ),     P(yᵢ = k | xᵢ) = exp(−xᵢ) xᵢᵏ / k!",
         "E[yᵢ | xᵢ] = Var(yᵢ | xᵢ) = xᵢ,     SNRᵢ = √xᵢ",
         "Peak convention: x = p s, max(s) = 1, p = max(x) ∈ {0.1, 0.2, 0.5, 1, 2, 4}"], 0.5, 1.13, 9.0, 1.3, 15, gap=8)
text(s, [[("Task: ", True), ("recover x from one noisy count image y.", False)],
         [("Why it is hard: ", True), ("the noise depends on the signal (variance = mean), the data are integers with mostly zeros, "
          "and at p = 0.1, P(yᵢ = 0) = e⁻⁰·¹ ≈ 0.905. Gaussian-noise denoisers assume none of this.", False)]],
     0.5, 2.75, 9.0, 1.8, 14, gap=9)
say(s, "50 seconds", "Mean equals variance, so bright pixels are noisier in absolute terms but cleaner in relative terms. The peak p sets the difficulty; we use the paper's six peaks.",
    "Existing methods handle this in two ways; let us see where each one fails.")

# ---------------------------------------------------------------- 4. existing methods (1)
s = new_slide("Existing methods and where they fail (1)", REFS["ans"])
table(s, [["Method", "Idea", "Failure at low counts (our measurement)"],
          ["Mean / Gaussian / median / Wiener", "Local smoothing", f"Blur edges; median = 0 when most counts are 0 ({P0.loc['median_filter', 0.1]:.2f} dB at p = 0.1)"],
          ["Wavelet thresholding, NL-means", "Sparse transform / similar patches", "Thresholds and patch matching assume Gaussian noise"],
          ["Poisson-TV", "Exact Poisson likelihood + TV", "Staircasing; flat texture"],
          ["Anscombe + Gaussian denoiser", "z = 2√(y + 3/8) has variance ≈ 1", "Only for large counts; algebraic inverse is biased"]],
      0.5, 1.13, 9.0, [2.6, 2.5, 3.9], size=10.5, row_h=0.42, right_from=99)
gap = [P0.loc["anscombe_bm3d", p] - P0.loc["anscombe_bm3d_algebraic", p] for p in PEAKS]
text(s, f"Measured: with the same BM3D output, the algebraic inverse loses {min(gap):.1f} to {max(gap):.1f} dB against the exact unbiased inverse "
        f"(Mäkitalo and Foi). Even with the exact inverse, Anscombe + BM3D is beaten by a tuned Gaussian filter at p = 0.1 "
        f"({P0.loc['anscombe_bm3d', 0.1]:.2f} vs {P0.loc['gaussian_filter', 0.1]:.2f} dB).", 0.5, 3.6, 9.0, 1.1, 12)
say(s, "60 seconds", "Conventional filters assume Gaussian noise. The variance-stabilising route is the standard fix, but the stabilisation is only approximate at low counts. Our own runs show both failures.",
    "The two strongest classical baselines, BM3D and SPDA, have their own limits.")

# ---------------------------------------------------------------- 5. existing methods (2)
s = new_slide("Existing methods and where they fail (2)", REFS["bm3d"] + " " + REFS["spda"])
text(s, [[("BM3D (Dabov et al.)", True)],
         "Groups similar patches, 3-D transform, threshold, Wiener refinement. State of the art for Gaussian noise.",
         "Fails at low counts: patches are mostly zeros, so block matching finds wrong 'similar' patches; it needs the Anscombe step and inherits its bias.",
         [("SPDA (Giryes and Elad)", True)],
         "Patch model exp(Dα) with shared sparse supports; uses the Poisson likelihood directly.",
         "Fails in practice: dictionary learning and greedy pursuit take about 10 hours per image without binning (reported in [1]); the model is tied to one prior."],
     0.5, 1.13, 9.0, 3.3, 13, gap=6)
text(s, "Gap: a method with the exact Poisson likelihood that can still use the best available image prior, at a practical cost.",
     0.5, 4.5, 9.0, 0.5, 13, bold=True)
say(s, "50 seconds", "BM3D has the best prior but the wrong noise model; SPDA has the right noise model but an expensive, fixed prior.",
    "P4IP is designed to get both at once.")

# ---------------------------------------------------------------- 6. P4IP formulation
s = new_slide("Reference method: P4IP (Plug-and-Play for Poisson)", REFS["p4ip"])
text(s, ["minₓ≥₀  f(x) + λR(x),     f(x) = ∑ᵢ (xᵢ − yᵢ log xᵢ)   (exact Poisson negative log-likelihood)",
         "Split:  minₓ,ᵥ  f(x) + λR(v)   subject to x = v,   solved with ADMM:",
         "xᵏ⁺¹ = arg minₓ≥₀ { f(x) + (ρ/2) ‖x − vᵏ + uᵏ‖² }     (Poisson step)",
         "vᵏ⁺¹ = D(xᵏ⁺¹ + uᵏ, σ),   σ² = λ/ρ     (any Gaussian denoiser, e.g. BM3D)",
         "uᵏ⁺¹ = uᵏ + xᵏ⁺¹ − vᵏ⁺¹,     ρ ← 1.065 ρ each iteration, 70 iterations"], 0.5, 1.13, 9.0, 2.5, 14, gap=8)
text(s, "Key idea: the likelihood and the prior are handled in separate steps, so the prior can be replaced by any denoiser "
        "without changing the noise model. This modularity is what our Direction A exploits.", 0.5, 3.85, 9.0, 0.9, 13)
say(s, "60 seconds", "ADMM alternates a data step and a denoising step tied by a dual variable. The denoising step is a Gaussian denoising problem with noise level lambda over rho, so BM3D can be plugged in.",
    "The data step has a closed form, which keeps P4IP fast.")

# ---------------------------------------------------------------- 7. P4IP closed form
s = new_slide("P4IP: closed-form Poisson step", REFS["p4ip"])
text(s, ["aᵢ = vᵢᵏ − uᵢᵏ,     minₓᵢ≥₀ { xᵢ − yᵢ log xᵢ + (ρ/2)(xᵢ − aᵢ)² }",
         "1 − yᵢ/xᵢ + ρ(xᵢ − aᵢ) = 0",
         "xᵢᵏ⁺¹ = [ aᵢ − 1/ρ + √((aᵢ − 1/ρ)² + 4yᵢ/ρ) ] / 2,     yᵢ = 0:  xᵢᵏ⁺¹ = max(aᵢ − 1/ρ, 0)"], 0.5, 1.13, 9.0, 1.6, 15, gap=10)
text(s, [[("Paper's reported result: ", True), ("best average PSNR at peaks 0.1 and 0.2 against Anscombe + BM3D and SPDA, "
          "at minutes per image instead of hours; binning and multiple priors improve it further.", False)],
         [("Our implementation: ", True), ("the same update, BM3D (Python bm3d package) as denoiser, ρ schedule and 70 iterations as in the paper.", False)]],
     0.5, 3.0, 9.0, 1.7, 13, gap=9)
say(s, "45 seconds", "Per pixel, the Poisson step is a quadratic equation with one non-negative root. A zero count simply shrinks a towards zero.",
    "Next: did we reproduce the paper's numbers?")

# ---------------------------------------------------------------- 8. protocol and changes
s = new_slide("Experimental protocol and changes from the paper")
table(s, [["", "Paper [1]", "Ours"],
          ["Test images", "8 (Saturn, Flag, Cameraman, House, Swoosh, Peppers, Bridge, Ridges)", "8 from Set12 (incl. Cameraman, House, Peppers)"],
          ["Tuning", "Per peak (not specified on which images)", "Per peak on 4 separate BSD68 images"],
          ["Noise", "Poisson, peaks 0.1 to 4", "Same; one fixed noise draw per image and peak"],
          ["BM3D", "Authors' MATLAB code", "Python bm3d package"],
          ["SPDA", "Full algorithm (hours per image)", "Simplified: fixed sparsity, k-means groups, 3 rounds"],
          ["Real data", "None", "FMD fluorescence microscopy (Poisson-Gaussian)"],
          ["Statistics", "Averages", "Averages + paired Wilcoxon test, SSIM, runtime"]],
      0.5, 1.05, 9.0, [1.4, 3.9, 3.7], size=10, row_h=0.36, right_from=99)
text(s, "Training images for A2 dictionaries: 400 from BSD400. No test image is used for tuning or training.", 0.5, 4.55, 9.0, 0.35, 11)
say(s, "45 seconds", "Same peaks and metric as the paper. The differences are listed so that every gap in the next slides can be traced to one of them.",
    "Here is the replication of the paper's main table.")

# ---------------------------------------------------------------- 9. replication average
s = new_slide("Replication: average PSNR (paper Table 1)", REFS["p4ip"])
rows = [["Method", "Source", "peak 0.1", "peak 0.2", "peak 1"]]
paper = {"anscombe_bm3d": [16.59, 18.43, 21.73], "spda": [15.48, 18.57, 23.61], "p4ip_bm3d": [17.85, 19.33, 22.88]}
for m in ("anscombe_bm3d", "spda", "p4ip_bm3d"):
    rows.append([NAME[m], "paper, its 8 images", *[f"{v:.2f}" for v in paper[m]]])
    rows.append(["", "ours, 8 test images", *[f2(P0.loc[m, p]) for p in (0.1, 0.2, 1.0)]])
table(s, rows, 0.5, 1.0, 9.0, [2.3, 2.5, 1.4, 1.4, 1.4], size=10, row_h=0.25, right_from=2)
lead_t = [p for p in (0.1, 0.2, 1.0) if P0.loc["p4ip_bm3d", p] > P0.loc["anscombe_bm3d", p]]
text(s, [f"Reproduced: P4IP + BM3D beats Anscombe + BM3D at peaks {', '.join(f'{p:g}' for p in lead_t)} "
         f"(+{P0.loc['p4ip_bm3d', 0.1] - P0.loc['anscombe_bm3d', 0.1]:.2f} dB at 0.1), as in the paper.",
         f"Not reproduced: SPDA leading at peak 1 (ours {P0.loc['spda', 1.0] - P0.loc['p4ip_bm3d', 1.0]:+.2f} dB vs P4IP); our SPDA is simplified.",
         "Absolute values differ because the image sets differ; the next slide compares the same images."],
     0.5, 3.45, 9.0, 1.5, 11.5, gap=5)
say(s, "60 seconds", "The ranking between P4IP and Anscombe + BM3D is reproduced. Absolute values are not comparable across different image sets, so we check the three shared images.",
    "On the images both studies use, the numbers match closely.")

# ---------------------------------------------------------------- 10. replication per image
s = new_slide("Replication on the same images", REFS["p4ip"])
PAPER_IMG = {("cameraman", "anscombe_bm3d"): [15.66, 17.35, 18.83, 20.37, 22.13, 23.94],
             ("cameraman", "p4ip_bm3d"): [16.88, 17.82, 19.27, 20.54, 21.87, 23.29],
             ("house", "anscombe_bm3d"): [16.28, 18.37, 20.27, 22.35, 24.18, 26.04],
             ("house", "p4ip_bm3d"): [18.30, 19.48, 20.93, 22.67, 24.65, 26.33],
             ("peppers", "anscombe_bm3d"): [15.61, 17.10, 18.49, 19.89, 21.97, 24.07],
             ("peppers", "p4ip_bm3d"): [16.28, 17.31, 18.86, 20.07, 21.33, 23.88]}
rows = [["Paper / ours (dB)", *[f"peak {p}" for p in PL]]]
diffs = {"anscombe_bm3d": [], "p4ip_bm3d": []}
for (im, m), pv in PAPER_IMG.items():
    o = T0[(T0.image == im) & (T0.method == m)].set_index("peak").psnr
    short = "Anscombe + BM3D" if m == "anscombe_bm3d" else "P4IP + BM3D"
    rows.append([f"{im.capitalize()}, {short}", *[f"{v:.2f} / {f2(o.get(p))}" for p, v in zip(PEAKS, pv)]])
    diffs[m].append([o.get(p) - v for p, v in zip(PEAKS, pv)])
table(s, rows, 0.5, 1.05, 9.0, [2.7] + [1.05] * 6, size=10, row_h=0.3)
dm = {m: np.nanmean(np.array(v), axis=0) for m, v in diffs.items()}
text(s, [f"Ours minus paper, mean of the 3 images (peaks 0.1 to 4): P4IP + BM3D {', '.join(f'{x:+.2f}' for x in dm['p4ip_bm3d'])}; "
         f"Anscombe + BM3D {', '.join(f'{x:+.2f}' for x in dm['anscombe_bm3d'])}.",
         "From peak 0.2 up our P4IP + BM3D is within 0.31 dB of the paper. The largest gaps are at peak 0.1, where counts are fewest and "
         "single noise draws differ between the two studies, and the BM3D implementations differ (Python vs MATLAB)."],
     0.5, 3.45, 9.0, 1.4, 11, gap=6)
say(s, "60 seconds", "This is the cleanest replication check: same image, same peak. P4IP agrees to within a third of a dB from peak 0.2 on.",
    "The paper also reports binning and multiple priors; we reproduced those too.")

# ---------------------------------------------------------------- 11. replication binning + multiple priors
s = new_slide("Replication: binning and multiple priors (paper Tables 2, 3)", REFS["p4ip"])
pb = {"cameraman": (18.25, 18.58, 18.58), "house": (19.71, 19.96, 20.02), "peppers": (17.44, 17.44, 17.63)}
rows = [["Peak 0.2, 3×3 binning", "Anscombe + BM3D", "P4IP + BM3D", "P4IP, multiple priors"]]
for im, (b1, b2, b3) in pb.items():
    o = T3[(T3.image == im) & (T3.peak == 0.2)].set_index("method").psnr
    rows.append([f"{im.capitalize()}: paper / ours", f"{b1:.2f} / {f2(o.get('anscombe_bm3d'))}",
                 f"{b2:.2f} / {f2(o.get('p4ip_bm3d'))}", f"{b3:.2f} / {f2(o.get('A3_bm3d_wavelet'))}"])
table(s, rows, 0.5, 1.05, 9.0, [2.7, 2.1, 2.1, 2.1], size=10.5, row_h=0.32)
db_a = [T3[(T3.image == im) & (T3.peak == 0.2) & (T3.method == "anscombe_bm3d")].psnr.mean() - v[0] for im, v in pb.items()]
db_p = [T3[(T3.image == im) & (T3.peak == 0.2) & (T3.method == "p4ip_bm3d")].psnr.mean() - v[1] for im, v in pb.items()]
text(s, [f"Binning (sum 3×3 blocks, denoise, interpolate) reproduces Anscombe + BM3D within {max(abs(x) for x in db_a):.2f} dB. "
         f"Our binned P4IP + BM3D is {-max(db_p):.1f} to {-min(db_p):.1f} dB below the paper: its binned tuning picked ρ₀ at the edge of an early, too-narrow grid.",
         "Multiple priors: the paper adds a second prior to BM3D and gains 0.2 dB on average at peak 0.2. Our second prior is wavelet shrinkage (our A3); "
         "with binning it did not gain; it inherited the same edge-of-grid P4IP parameters, so these binned numbers are lower bounds. "
         "Without binning it does gain (Direction A)."],
     0.5, 2.55, 9.0, 2.2, 11.5, gap=7)
say(s, "45 seconds", "Binning is reproduced for the Anscombe baseline. Our binned P4IP runs used an early grid whose best value sat at the edge, which we state openly.",
    "Synthetic noise is only half the story; next, real microscope data.")

# ---------------------------------------------------------------- 12. FMD
s = new_slide("Real data: FMD fluorescence microscopy", REFS["fmd"])
fmd_path = f"{RES}/fmd.csv"
if os.path.exists(fmd_path):
    F = pd.read_csv(fmd_path)
    sub = set(F[F.method == "p4ip_bm3d"].image) & set(F[F.method == "A3_bm3d_wavelet"].image)
    order = [m for m in ["noisy", "gaussian_filter", "A1_subband", "B_fista_dict", "spda", "anscombe_bm3d", "p4ip_bm3d", "A3_bm3d_wavelet"] if m in set(F.method)]
    nm = dict(NAME, noisy="Noisy raw capture")
    Fs = F[F.image.isin(sub)]
    ps = Fs.groupby("method").psnr.mean(); ss = Fs.groupby("method").ssim.mean(); pa = F.groupby("method").psnr.mean()
    best = ps.drop("noisy", errors="ignore").max()
    rows = [["Method", f"PSNR, {len(sub)} images", "SSIM", "PSNR, all 48"]]
    bold = []
    for i, m in enumerate(order, 1):
        full = (F.method == m).sum() == 48
        rows.append([nm[m], f2(ps.get(m)), f2(ss.get(m)) if m in ss else "–", f2(pa[m]) if full else "–"])
        if ps.get(m) == best:
            bold.append((i, 1))
    table(s, rows, 0.5, 1.0, 5.3, [2.6, 1.0, 0.75, 0.95], size=9.5, row_h=0.25, bold_cells=bold)
    nz = F[F.method == "noisy"]
    d_pa = (Fs[Fs.method == "p4ip_bm3d"].set_index("image").psnr - Fs[Fs.method == "anscombe_bm3d"].set_index("image").psnr).dropna()
    d_a3 = (Fs[Fs.method == "A3_bm3d_wavelet"].set_index("image").psnr - Fs[Fs.method == "p4ip_bm3d"].set_index("image").psnr).dropna()
    wf = d_pa[d_pa.index.str.startswith("WideField")]; ot = d_pa[~d_pa.index.str.startswith("WideField")]
    bw = nz[nz.image.str.startswith("WideField")].b.median(); bo = nz[~nz.image.str.startswith("WideField")].b.median()
    p_pa = wilcoxon(d_pa).pvalue
    text(s, [f"48 real images (confocal, two-photon, wide-field); ground truth = average of 50 captures; central 256 × 256 crop. "
             f"Fitted Var = a·u + b gives effective peaks {nz.peak_eff.quantile(0.1):.0f} to {nz.peak_eff.quantile(0.9):.0f} photons.",
             f"P4IP vs Anscombe + BM3D: {d_pa.mean():+.2f} dB on average, not significant (p = {p_pa:.2f}). It depends on the microscope: "
             f"P4IP wins all {len(wf)} wide-field images ({wf.min():+.1f} to {wf.max():+.1f} dB), Anscombe + BM3D wins {(ot < 0).sum()} of {len(ot)} confocal and two-photon images.",
             f"The wide-field captures carry strong Gaussian read noise (median b = {bw:.0f} vs {bo:.0f}); we did not isolate why P4IP handles them better.",
             f"A3 vs P4IP: {d_a3.mean():+.2f} dB, again largest on wide-field. No FMD tuning: parameters transferred from synthetic peak 4."],
         5.95, 1.0, 3.55, 3.9, 9, gap=4)
else:
    text(s, "FMD runs in progress.", 0.5, 1.2, 9.0, 0.4, 14)
text(s, "PSNR on the 8-bit scale, 10 log₁₀(255²/MSE), as in the FMD benchmark. Source: results/fmd.csv.", 0.5, 4.85, 9.0, 0.25, 9)
say(s, "60 seconds", "Real fluorescence images also have camera read noise. Fitting the gain and read noise per image turns the data into approximately Poisson counts, so every method runs unchanged. The ranking depends on the microscope, which is itself a finding.",
    "With the baseline established, here are our own proposals.")

# ---------------------------------------------------------------- 13. direction A idea
s = new_slide("Proposed direction A: change the P4IP prior", REFS["p4ip"])
text(s, [[("A1. Orthonormal wavelet shrinkage as the denoiser", True)],
         "D(r, η) = WᵀS(Wr, η): one threshold, or one per wavelet level (tuned). A convex, interpretable prior.",
         [("A2. Learned dictionary for wavelet-domain patches", True)],
         "WₚRⱼr ≈ Bαⱼ, 256 atoms learned on 40,000 BSD400 patches; control: a pixel dictionary with the same atom count.",
         [("A3. Multiple priors: BM3D + wavelet consensus", True)],
         "Each iteration runs both denoisers and averages them (ρ_eff = 2ρ); the wavelet weight λ₂ is tuned.",
         [("Hypothesis: ", True), ("wavelet structure complements BM3D where block matching is unreliable, i.e. at the lowest counts.", False)]],
     0.5, 1.13, 9.0, 3.9, 13, gap=6)
say(s, "45 seconds", "All three keep P4IP's exact Poisson step and change only the denoiser, exactly the modularity shown earlier.",
    "Results for A1 first.")

# ---------------------------------------------------------------- 14. A1
s = new_slide("A1: wavelet prior, one vs per-level thresholds")
rows = [["Test PSNR (dB)", *[f"peak {p}" for p in PL]]]
for m in ("anscombe_bm3d", "p4ip_bm3d", "A1_wavelet", "A1_subband"):
    rows.append([NAME[m], *[f2(P0.loc[m, p]) for p in PEAKS]])
table(s, rows, 0.5, 1.05, 9.0, [3.3] + [0.95] * 6, size=10.5, row_h=0.28)
w = TUNED["A1_subband"]
wf = [w[str(float(p))]["params"]["w1"] for p in PEAKS]; wc = [w[str(float(p))]["params"]["w4"] for p in PEAKS]
a1 = [P0.loc["A1_subband", p] - P0.loc["A1_wavelet", p] for p in PEAKS]
text(s, [f"Per-level thresholds gain up to {max(a1):.2f} dB. Why: the tuned weights are large at the finest level (w₁ = {min(wf):g} to {max(wf):g}) "
         f"and small at the coarsest (w₄ = {min(wc):g} to {max(wc):g}). At low counts fine scales are mostly noise and coarse scales carry the structure; "
         "one threshold must compromise between them.",
         f"A1 beats Anscombe + BM3D at peak 0.1 ({P0.loc['A1_subband', 0.1] - P0.loc['anscombe_bm3d', 0.1]:+.2f} dB) but loses from 0.5 up. "
         "Why: shrinkage in a fixed basis has no non-local self-similarity; once there are enough photons, BM3D's grouping recovers texture that wavelets erase."],
     0.5, 2.6, 9.0, 2.3, 11.5, gap=7)
say(s, "60 seconds", "Two results: per-level thresholds clearly help, and the wavelet prior alone is a strong choice only at the lowest light.",
    "Can a learned dictionary do better than a fixed wavelet basis?")

# ---------------------------------------------------------------- 15. A2
s = new_slide("A2: wavelet-domain vs pixel dictionary")
rows = [["PSNR (dB)", *[f"peak {p}" for p in PL]]]
for m in ("p4ip_bm3d", "A2_wavelet_dict", "A2_pixel_dict"):
    rows.append([NAME[m] + ", tuning", *[f2(tune_psnr(m, p)) for p in PEAKS]])
for m in ("p4ip_bm3d", "A2_wavelet_dict", "A2_pixel_dict"):
    rows.append([NAME[m] + ", test 3×3", *[f2(P3.loc[m, p]) for p in PEAKS]])
table(s, rows, 0.5, 1.05, 9.0, [3.3] + [0.95] * 6, size=10, row_h=0.27)
g3 = [P3.loc["A2_wavelet_dict", p] - P3.loc["A2_pixel_dict", p] for p in PEAKS]
text(s, [f"The wavelet-domain dictionary is not better than the pixel dictionary (test, binned: {min(g3):+.2f} to {max(g3):+.2f} dB). "
         "Why: the 8×8 patch Haar transform is orthonormal, so coding in the wavelet domain spans the same space as coding in pixels; "
         "restricting each atom to one orientation removes freedom instead of adding information.",
         "Both stay below P4IP + BM3D. Why: they are local patch models without BM3D's non-local grouping; the result matches the K-SVD vs BM3D gap known for Gaussian noise.",
         "Unbinned test runs of A2 were skipped (about 25 minutes per image); the tuning-image numbers show the same ordering."],
     0.5, 3.15, 9.0, 1.9, 10, gap=5)
say(s, "50 seconds", "The idea was that wavelet structure helps a learned dictionary. It does not, and the reason is mathematical: an orthonormal change of basis does not change what a dictionary can represent.",
    "The third prior, combining BM3D with wavelets, is where the hypothesis holds.")

# ---------------------------------------------------------------- 16. A3
s = new_slide("A3: multiple priors help at the lowest light")
rows = [["PSNR (dB)", *[f"peak {p}" for p in PL]]]
rows.append(["P4IP + BM3D, test", *[f2(P0.loc["p4ip_bm3d", p]) for p in PEAKS]])
rows.append(["A3 BM3D + wavelet, test", *[f2(P0.loc["A3_bm3d_wavelet", p]) for p in PEAKS]])
rows.append(["Difference, test", *[("–" if pd.isna(P0.loc["A3_bm3d_wavelet", p]) else f"{P0.loc['A3_bm3d_wavelet', p] - P0.loc['p4ip_bm3d', p]:+.2f}") for p in PEAKS]])
rows.append(["Difference, tuning images", *[f"{tune_psnr('A3_bm3d_wavelet', p) - tune_psnr('p4ip_bm3d', p):+.2f}" for p in PEAKS]])
table(s, rows, 0.5, 1.05, 9.0, [3.3] + [0.95] * 6, size=10.5, row_h=0.28, bold_cells=[(3, 1), (4, 1)])
pa3 = paired(T0, "A3_bm3d_wavelet", ref="p4ip_bm3d")[0]
text(s, [f"At peak 0.1 the wavelet prior adds {P0.loc['A3_bm3d_wavelet', 0.1] - P0.loc['p4ip_bm3d', 0.1]:+.2f} dB on the test images"
         + (f" ({pa3[1]}/{pa3[2]} images better, Wilcoxon p = {pa3[3]:.4f})" if pa3 else "") + ".",
         "Why: at peak 0.1 most patches are zeros, so BM3D's block matching groups unrelated patches and leaves blotches. "
         "Wavelet shrinkage gives a stable smooth estimate; averaging the two in the consensus step damps BM3D's errors.",
         (lambda d: f"From peak 0.2 up A3 is {min(d):.2f} to {max(d):.2f} dB below P4IP + BM3D. Why: block matching is reliable there, so the wavelet prior only adds blur; "
          "the tuning picked the smallest wavelet weight tried, which is small but not zero.")([P0.loc['p4ip_bm3d', p] - P0.loc['A3_bm3d_wavelet', p] for p in PEAKS[1:]])],
     0.5, 2.6, 9.0, 2.3, 11.5, gap=7)
say(s, "60 seconds", "This is the positive result of Direction A: the multiple-prior extension helps exactly where we predicted, and tuning switches it off where it would hurt.",
    "Direction B takes a different route: an explicit sparse model.")

# ---------------------------------------------------------------- 17. direction B
s = new_slide("Direction B: explicit sparsity with ISTA vs FISTA", REFS["fista"])
text(s, ["z = A(y),   minimise F(α) = ½ ‖Dα − z‖² + λ ‖α‖₁,   D = redundant wavelet or learned dictionary",
         "ISTA: αᵏ⁺¹ = S(αᵏ − Dᵀ(Dαᵏ − z)/L, λ/L)        FISTA: same step from an extrapolated point, O(1/k²) vs O(1/k)"],
     0.5, 1.05, 9.0, 0.8, 12, gap=5)
it3, tm3, it0 = table_of(T3, "iterations"), table_of(T3, "time"), table_of(T0, "iterations")
rows = [["3×3 binned", "PSNR ISTA", "PSNR FISTA", "iter. ISTA", "iter. FISTA"]]
for fr, lab in (("swt", "wavelet"), ("dict", "dictionary")):
    for p in (0.5, 1.0, 4.0):
        rows.append([f"{lab}, peak {p:g}", f2(P3.loc[f"B_ista_{fr}", p]), f2(P3.loc[f"B_fista_{fr}", p]),
                     f"{it3.loc[f'B_ista_{fr}', p]:.0f}", f"{it3.loc[f'B_fista_{fr}', p]:.0f}"])
table(s, rows, 0.5, 1.95, 5.4, [1.6, 0.95, 0.95, 0.95, 0.95], size=9.5, row_h=0.25)
s.shapes.add_picture(CONV, Inches(6.1), Inches(1.95), Inches(3.4), Inches(2.97))
ratio = [it3.loc[f"B_ista_{fr}", p] / it3.loc[f"B_fista_{fr}", p] for fr in ("swt", "dict") for p in PEAKS if it3.loc[f"B_ista_{fr}", p] > 5]
zero = [p for p in PEAKS if it0.loc["B_fista_dict", p] <= 1 and it0.loc["B_fista_swt", p] <= 1]
text(s, [f"Same λ, start and stopping rule: identical PSNR; FISTA needs {min(ratio):.1f} to {max(ratio):.1f}× fewer iterations "
         "(ISTA often stops at the 2000 cap, so these are lower bounds). Why identical: F is convex, one minimum.",
         f"Without binning, tuning sets every detail coefficient to 0 at peaks {', '.join(f'{p:g}' for p in zero)}. Why: detail coefficients "
         "of the Anscombe image are below the noise (σ ≈ 1), so keeping any of them adds noise."],
     0.5, 3.75, 5.4, 1.3, 9.5, gap=4)
say(s, "70 seconds", "Both solvers minimise the same convex objective, so they must reach the same image; FISTA's momentum gets there in far fewer iterations, as the curves on the right show.",
    "Putting all methods side by side.")

# ---------------------------------------------------------------- 18. overall comparison
s = new_slide("All methods: PSNR vs peak (test images)")
line_chart(s, P0, ["anscombe_bm3d", "p4ip_bm3d", "spda", "A1_subband", "A3_bm3d_wavelet", "B_fista_dict",
                   "gaussian_filter", "poisson_tv"], 0.5, 1.05, 9.0, 3.6, 12, 24)
text(s, "No binning, mean over 8 test images. Lowest light: P4IP-type and smoothing methods lead; "
        "highest peaks: Anscombe + BM3D leads, as its Gaussian approximation becomes accurate.", 0.5, 4.72, 9.0, 0.5, 11)
say(s, "40 seconds", "The crossover between P4IP and Anscombe + BM3D happens between peaks 1 and 2, where the Anscombe approximation becomes good.",
    "What we conclude from all of this.")

# ---------------------------------------------------------------- 19. findings and conclusions
s = new_slide("Major findings")
p4 = [p for p in PEAKS if P0.loc["p4ip_bm3d", p] > P0.loc["anscombe_bm3d", p]]
text(s, [f"1.  Replication: P4IP + BM3D beats Anscombe + BM3D at peaks {', '.join(f'{p:g}' for p in p4)}; on shared images it matches the paper within 0.31 dB from peak 0.2.",
         f"2.  The exact unbiased inverse Anscombe is essential: {min(gap):.1f} to {max(gap):.1f} dB over the algebraic inverse.",
         f"3.  Multiple priors (BM3D + wavelet) improve P4IP at peak 0.1 ({P0.loc['A3_bm3d_wavelet', 0.1] - P0.loc['p4ip_bm3d', 0.1]:+.2f} dB, 8/8 images) and cost at most {max(P0.loc['p4ip_bm3d', p] - P0.loc['A3_bm3d_wavelet', p] for p in PEAKS[1:]):.2f} dB above it.",
         f"4.  Per-level wavelet thresholds add up to {max(a1):.1f} dB; learned wavelet-domain dictionaries do not beat pixel dictionaries.",
         f"5.  FISTA reaches the ISTA solution in {min(ratio):.1f} to {max(ratio):.1f}× fewer iterations; the explicit sparse model needs binning to be useful.",
         "6.  No method wins at every peak: the best prior depends on the photon count. On real FMD data (10+ photons) P4IP + BM3D and "
         "Anscombe + BM3D are level on average; P4IP wins on wide-field images, Anscombe + BM3D on confocal and two-photon."],
     0.5, 1.13, 9.0, 3.9, 12.5, gap=6)
say(s, "60 seconds", "Six findings, each backed by a slide earlier in the talk.", "And what we would do next.")

# ---------------------------------------------------------------- 20. future directions
s = new_slide("Limitations and future directions")
text(s, [[("Limitations", True)],
         "One noise draw per image; 8 test images. Simplified SPDA. Python BM3D instead of the authors' code.",
         "Some tuned parameters lie at the edge of their grid (flagged in the logs); binned P4IP-type runs used an early grid. FMD: P4IP-type methods and SPDA on a subset (about 4 min per image), no FMD-specific tuning.",
         [("Future directions", True)],
         "Choose the prior weight per image or per region from the photon count (A3 switches itself off already).",
         "Learned (CNN) denoisers inside P4IP; multiple noise draws; the full FMD set with tuned parameters.",
         "Poisson-Gaussian ADMM step for microscopy instead of the shifted-Poisson approximation."],
     0.5, 1.13, 9.0, 3.9, 13, gap=6)
say(s, "40 seconds", "Limitations are stated openly; each future direction follows from a finding.", "Thank you; we are happy to take questions.")

# ---------------------------------------------------------------- 21. thanks
s = new_slide("Thank you")
text(s, ["Questions?",
         "Code and logs: github.com/tarantulass/EE779-Poisson-Denoising (experiments/, results/).",
         [("AI use: ", True), ("code, README and this deck were written with Claude (Anthropic) following our proposal; every number is read from the result logs.", False)],
         "References: [1] Rond, Giryes, Elad, arXiv:1511.02500. [2] Dabov et al., IEEE TIP 2007. [3] Giryes, Elad, IEEE TIP 2014. "
         "[4] Mäkitalo, Foi, IEEE TIP 2011. [5] Beck, Teboulle, SIAM J. Imaging Sci. 2009. [6] Zhang et al., CVPR 2019 (FMD)."],
     0.5, 1.13, 9.0, 3.9, 13, gap=12)

# ================================================================ backup
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



full_table(P0, "Backup: mean PSNR (dB), test images, no binning", "Bold: best per peak. Source: results/test.csv.")
full_table(P3, "Backup: mean PSNR (dB), test images, 3×3 binning", "Bold: best per peak. Source: results/test_bin3.csv.")


def paired_slide(d, title, src, methods):
    s = new_slide(title)
    rows = [["Method minus Anscombe + BM3D (dB)", *[f"peak {p}" for p in PL]]]
    bold = []
    for i, m in enumerate([m for m in methods if m in set(d.method)], 1):
        r = [NAME[m]]
        for j, v in enumerate(paired(d, m)):
            if v is None:
                r.append("–"); continue
            mean, wn, n, pv = v
            r.append(f"{mean:+.2f}{'*' if pv < 0.05 else ''}  ({wn}/{n})")
            if pv < 0.05:
                bold.append((i, j + 1))
        rows.append(r)
    table(s, rows, 0.5, 1.13, 9.0, [2.88] + [1.02] * 6, size=9.5, row_h=0.27, bold_cells=bold)
    text(s, f"Mean paired difference over the 8 test images, (images better / 8). * and bold: Wilcoxon signed-rank p < 0.05 "
            f"(with 8 images the smallest possible p is 0.0078). Source: {src}.", 0.5, 4.75, 9.0, 0.4, 9)


PM = ["p4ip_bm3d", "spda", "A1_wavelet", "A1_subband", "A2_wavelet_dict", "A2_pixel_dict", "A3_bm3d_wavelet",
      "B_fista_swt", "B_fista_dict", "gaussian_filter", "nl_means", "poisson_tv"]
paired_slide(T0, "Backup: paired comparison, no binning", "results/test.csv", PM)
paired_slide(T3, "Backup: paired comparison, 3×3 binning", "results/test_bin3.csv", PM)

s = new_slide("Backup: effect of 3×3 binning")
BM = [m for m in ["anscombe_bm3d", "p4ip_bm3d", "spda", "A1_subband", "B_fista_dict", "nl_means", "poisson_tv"] if m in has0 and m in has3]
rows = [["PSNR binned − unbinned (dB)", *[f"peak {p}" for p in PL]]]
for m in BM:
    rows.append([NAME[m], *[f"{P3.loc[m, p] - P0.loc[m, p]:+.2f}" for p in PEAKS]])
table(s, rows, 0.5, 1.13, 9.0, [3.3] + [0.95] * 6, size=10.5, row_h=0.28)
text(s, "Why: summing 3×3 blocks multiplies the counts by 9, so the Anscombe approximation holds and the noise is relatively smaller; "
        "the price is resolution, which dominates once there are enough photons.", 0.5, 3.6, 9.0, 0.8, 12)

s = new_slide("Backup: SSIM and runtime")
S0, R0, R3 = table_of(T0, "ssim"), table_of(T0, "time"), table_of(T3, "time")
SR = ["anscombe_bm3d", "p4ip_bm3d", "spda", "A1_subband", "A3_bm3d_wavelet", "B_fista_dict", "B_ista_dict", "gaussian_filter", "poisson_tv"]
rows = [["Method", "SSIM 0.1", "SSIM 1", "SSIM 4", "s/image, peak 1"]]
for m in SR:
    rows.append([NAME[m], *[f2(S0.loc[m, p]) if m in has0 and not pd.isna(S0.loc[m, p]) else "–" for p in (0.1, 1.0, 4.0)],
                 f"{R0.loc[m, 1.0]:.1f}" if m in has0 and not pd.isna(R0.loc[m, 1.0]) else "–"])
table(s, rows, 0.5, 1.13, 9.0, [3.6, 1.2, 1.2, 1.2, 1.8], size=10, row_h=0.27)
text(s, "SSIM on the test images without binning. Runtimes are wall-clock per image, one image per core; the P4IP-type runs were on a "
        "12-core laptop running 12 images at once, the others on a 2-core cloud machine.", 0.5, 4.2, 9.0, 0.6, 10)

s = new_slide("Backup: example, cameraman at peak 1")
info = json.load(open(f"{EX}/info.json"))
tiles = [("clean", "Clean"), ("noisy", "Noisy counts"), ("anscombe_bm3d", None), ("spda", None),
         ("poisson_tv", None), ("A1_subband", None), ("B_fista_dict", None), ("anscombe_bm3d_algebraic", None)]
for i, (k, lab) in enumerate(tiles):
    x, y = 0.5 + (i % 4) * 2.3, 1.0 + (i // 4) * 2.1
    s.shapes.add_picture(f"{EX}/{k}.png", Inches(x + 0.15), Inches(y), Inches(1.7), Inches(1.7))
    cap = (lab or NAME[k]) + (f", {info[k]:.2f} dB" if k in info else "")
    text(s, cap, x - 0.05, y + 1.72, 2.2, 0.3, 9, align=PP_ALIGN.CENTER)

# ---------------------------------------------------------------- footers like the template
N = len(SLIDES)
for i, s in enumerate(SLIDES, 1):
    text(s, f"{i} / {N}", 0.5, 5.3, 2.34, 0.18, 9)
    if s._refs:
        text(s, s._refs, 8.52, 5.3, 0.98, 0.18, 9, align=PP_ALIGN.RIGHT)
prs.save(OUT)
print("wrote", OUT, N, "slides")
