import fs from 'node:fs/promises';
import path from 'node:path';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
import { finalizePresentation } from '/home/jinx/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations/container_tools/artifact_tool_utils.mjs';

const root='/home/jinx/Documents/sem9/ee779/EE779-Poisson-Denoising';
const build=path.join(root,'.presentation-build');
const skill='/home/jinx/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const python='/home/jinx/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
process.env.RUNTIME_NODE_MODULES='/home/jinx/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE='/home/jinx/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';
process.env.RUNTIME_PYTHON=python;
const p=Presentation.create({slideSize:{width:1280,height:720}});
const refs={
  1:'Rond, A., Giryes, R., and Elad, M. Poisson Inverse Problems by the Plug-and-Play scheme. Supplied arXiv v1 (2015), arXiv:1511.02500. https://arxiv.org/abs/1511.02500 . Journal version: JVCIR 41 (2016), 96–108, https://doi.org/10.1016/j.jvcir.2016.09.009 . Numerical results in this deck come specifically from Tables 1 and 3 of the supplied 2015 preprint.',
  2:'Dabov, K., Foi, A., Katkovnik, V., and Egiazarian, K. Image Denoising by Sparse 3-D Transform-Domain Collaborative Filtering. IEEE TIP 16(8), 2080–2095 (2007). https://webpages.tuni.fi/foi/GCF-BM3D/BM3D_TIP_2007.pdf . DOI: 10.1109/TIP.2007.901238.',
  3:'Giryes, R., and Elad, M. Sparsity Based Poisson Denoising with Dictionary Learning. IEEE TIP 23(12), 5055–5066 (2014). https://arxiv.org/abs/1309.4306 . The method is SPDA, Sparse Poisson Denoising Algorithm.',
  4:'Mäkitalo, M., and Foi, A. Optimal Inversion of the Anscombe Transformation in Low-Count Poisson Image Denoising. IEEE TIP 20(1), 99–109 (2011). https://webpages.tuni.fi/foi/papers/OptAnscombeInverse-IEEE_TIP-Preprint.pdf . DOI: 10.1109/TIP.2010.2056693.',
  5:'Venkatakrishnan, S. V., Bouman, C. A., and Wohlberg, B. Plug-and-Play Priors for Model Based Reconstruction. IEEE GlobalSIP (2013), 945–948. https://brendt.wohlberg.net/publications/pdf/venkatakrishnan-2013-plugandplay.pdf . DOI: 10.1109/GlobalSIP.2013.6737048.',
  6:'Beck, A., and Teboulle, M. A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse Problems. SIAM J. Imaging Sciences 2(1), 183–202 (2009). https://www.tau.ac.il/~becka/FISTA.pdf . DOI: 10.1137/080716542.',
  7:'Ta, C.-K., Aich, A., Gupta, A., and Roy-Chowdhury, A. K. Poisson2Sparse: Self-Supervised Poisson Denoising From a Single Image (2022). Supplied paper, arXiv:2206.01856v2. https://arxiv.org/abs/2206.01856 . Related work only, not the proposed algorithm.'
};
const times=[20,50,35,40,45,45,50,55,30,60,80,60,30];
function text(s,str,x,y,w,h,size=26,bold=false,font='Arial',align='left'){
 const sh=s.shapes.add({name:`text-${s.shapes.items?.length??0}`,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=str; sh.text.style={typeface:font,fontSize:size,color:'#000000',bold,alignment:align,verticalAlignment:'top',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}}; return sh;
}
function slide(title,source=[],notes='',backup=false){
 const s=p.slides.add();s.background.fill='#FFFFFF'; const n=p.slides.items.length;
 text(s,title,64,42,1152,68,40,true);
 text(s,backup?'Backup / references':`${n} / 13`,64,678,300,23,16);
 if(source.length)text(s,source.map(i=>`[${i}]`).join(' '),1090,678,125,23,16,false,'Arial','right');
 s.speakerNotes.textFrame.setText((n<=13?`Suggested time: ${times[n-1]} seconds.\n\n`:'Backup slide, outside the 10-minute talk.\n\n')+notes+'\n\nSources\n'+source.map(i=>refs[i]).join('\n\n'));
 return s;
}
function eq(s,str,y,size=30,h=60){return text(s,str,84,y,1112,h,size,false,'DejaVu Serif');}
function line(s,str,y,h=62,size=26){return text(s,str,64,y,1152,h,size);}
function label(s,str,y){return text(s,str,64,y,1152,36,27,true);}
function table(s,values,y,widths,height=270,size=23){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top:y,width:1152,height,values,columnWidths:widths});
 t.styleOptions={headerRow:false,bandedRows:false,firstColumn:false};
 t.borders.assign({fill:'#000000',width:0.7,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const cell=t.getCell(r,c);cell.fill='#FFFFFF';cell.text.style={typeface:'Arial',fontSize:size,color:'#000000',bold:r===0,verticalAlignment:'middle',autoFit:'none'};
 }
 return t;
}

{
 const s=slide('Poisson image denoising',[1],
 'We study image denoising when photon counts are small. I will start with the Poisson noise model, review conventional denoising and the BM3D and SPDA approaches, and then explain P4IP. The project directions are to change the prior through wavelets or learned dictionaries, or to formulate an explicit sparse optimization problem for ISTA and FISTA. The proposed extensions have not yet been evaluated.');
 text(s,'Plug-and-play priors and sparse representations',64,157,1135,100,38);
 text(s,'EE779 · Project proposal',64,292,1135,45,26);
 line(s,'Poisson properties and conventional methods',406);
 line(s,'BM3D, SPDA, and the P4IP solution',470);
 line(s,'Proposed wavelet, dictionary, and ISTA/FISTA experiments',534);
}
{
 const s=slide('Poisson noise: signal-dependent uncertainty',[1],
 'Let x_i be the expected photon count at a pixel and y_i the observed count. Conditional on the image, we assume independent Poisson observations. The mean and variance are both x_i. Brighter pixels have larger absolute variance, but their relative noise is smaller. Here SNR means mean divided by standard deviation, so it equals the square root of x_i. At an expected count of 0.1, the probability of observing zero is about 90.5 percent. We use x = p s, where s has maximum one, to set the peak photon level p. Lower p makes the recovery harder.');
 eq(s,'yᵢ ∼ Poisson(xᵢ),     P(yᵢ = k | xᵢ) = exp(−xᵢ) xᵢᵏ / k!',145,29);
 eq(s,'E[yᵢ | xᵢ] = Var(yᵢ | xᵢ) = xᵢ',240,32);
 eq(s,'SNRᵢ = √xᵢ,     relative standard deviation = 1 / √xᵢ',330,29);
 line(s,'At xᵢ = 0.1 photons/pixel: P(yᵢ = 0) = exp(−0.1) ≈ 0.905.',432);
 line(s,'Peak convention: x = p s, with max(s) = 1 and p = max(x).',510);
 line(s,'Low counts produce many zeros and strongly non-Gaussian observations.',584,55,25);
}
{
 const s=slide('Conventional image denoising methods',[1,2],
 'Conventional methods differ in the image structure they assume. Local averaging and Gaussian smoothing rely on smoothness and blur fine features. A median filter is useful for impulsive noise but does not match the Poisson likelihood. Wiener filtering uses second-order signal and noise statistics. Wavelet shrinkage assumes sparse transform coefficients. Total variation favours sparse image gradients and can use an exact Poisson data term. Non-local means averages similar patches. For Poisson data we must adapt the noise model or first stabilize the variance.');
 table(s,[['Method','Assumption / operation','Main limitation'],['Mean / Gaussian / median','Local smoothing or order statistics','Edges and texture can disappear'],['Wiener filtering','Signal and noise second-order statistics','Needs a suitable variance model'],['Wavelet thresholding','Sparse multiscale coefficients','Thresholds depend on the noise model'],['Total variation (TV)','Sparse spatial gradients','Can flatten texture / create staircasing'],['Non-local means','Average pixels from similar patches','Patch matching is difficult at low counts']],151,[294,467,391],368,23);
 eq(s,'Poisson–TV:   minₓ≥₀  ∑ᵢ (xᵢ − yᵢ log xᵢ) + λ TV(x)',560,27);
}
{
 const s=slide('Variance stabilization and its limitations',[1,4],
 'A standard route is to transform the counts, use a Gaussian denoiser, and invert the transformation. The Anscombe transform makes variance approximately one when counts are sufficiently large. The delta-method expression shown explains the approximation, not an exact variance identity. After denoising, the algebraic inverse can introduce bias. Mäkitalo and Foi provide an exact unbiased inverse mapping for the expected transformed counts. That inverse improves the baseline, but does not make the transformed observations exactly Gaussian at low counts. This motivates keeping the original Poisson likelihood.');
 eq(s,'zᵢ = A(yᵢ) = 2 √(yᵢ + 3/8)',149,34);
 eq(s,'Var[A(yᵢ)] ≈ xᵢ / (xᵢ + 3/8) ≈ 1    at high counts',245,28);
 line(s,'1. Apply A to the counts.   2. Denoise z assuming σ ≈ 1.',353);
 line(s,'3. Map the estimate back using an appropriate inverse Anscombe.',420);
 line(s,'The algebraic inverse z²/4 − 3/8 can bias denoised estimates.',493);
 line(s,'An unbiased inverse helps, but the low-count Gaussian approximation remains imperfect.',564,73,26);
}
{
 const s=slide('BM3D: non-local collaborative filtering',[2],
 'BM3D stands for block matching and three-dimensional filtering. It stacks similar two-dimensional patches to form a three-dimensional group. The transform makes the shared structure sparse, and filtering suppresses small noisy coefficients. The first stage uses hard thresholding. A second stage uses the basic estimate for grouping and Wiener coefficients, while filtering groups from the noisy image. Weighted aggregation combines the overlapping estimates. BM3D supplies a strong Gaussian denoiser, used after Anscombe or as the denoising step inside P4IP.');
 line(s,'1. Find similar 2-D patches and stack them into a 3-D group G.',150);
 line(s,'2. Apply a 3-D transform, threshold, and invert the transform.',220);
 eq(s,'Ĝ = T⁻¹ hard(TG, τσ),     T is the 3-D transform',300,34);
 line(s,'3. Aggregate overlapping patch estimates to form a basic image.',402);
 line(s,'4. Refine with collaborative Wiener filtering guided by the basic image.',473);
 line(s,'Poisson use: Anscombe + BM3D, or BM3D inside the P4IP iteration.',561,65,27);
}
{
 const s=slide('SPDA: sparse Poisson dictionary learning',[3],
 'The correct acronym is SPDA. For a noisy patch q_j, the clean patch is represented as exp(D alpha_j), with the exponential applied elementwise. This guarantees positive intensity. Substitution into the Poisson negative log-likelihood gives the displayed sparse coding objective. SPDA uses a greedy pursuit, shared supports for similar patches, bootstrapped stopping, and dictionary updates. It therefore adapts sparse modelling directly to Poisson data, at greater computational cost than a simple transform baseline.');
 eq(s,'Clean patch pⱼ = exp(Dαⱼ),     ‖αⱼ‖₀ ≤ K',157,31);
 eq(s,'min over αⱼ:  1ᵀ exp(Dαⱼ) − qⱼᵀDαⱼ,   ‖αⱼ‖₀ ≤ K',259,28);
 line(s,'D is a learned dictionary. αⱼ contains a few active coefficients.',362);
 line(s,'Group similar patches and use a greedy pursuit with shared supports.',430);
 line(s,'Alternate sparse coding and dictionary updates, then aggregate patches.',498);
 line(s,'Uses the Poisson likelihood directly. Learning and pursuit add computation.',566,65,25);
}
{
 const s=slide('P4IP: separate the likelihood and the prior',[1,5],
 'We first write a MAP-inspired objective with Poisson data fidelity f and a prior penalty lambda R. The zero-intensity convention is zero times log zero equals zero, and positive observations at zero predicted intensity have infinite cost. Introduce a second image v and enforce x equals v. ADMM alternates a likelihood update, a proximal prior update, and a scaled dual update. The prior subproblem has the form of Gaussian denoising with variance lambda over rho. Plug-and-play substitutes an available denoiser for that subproblem. An arbitrary denoiser need not correspond to an explicit R, so this substitution does not automatically inherit convex ADMM guarantees.');
 eq(s,'minₓ≥₀  f(x) + λR(x),     f(x) = ∑ᵢ (xᵢ − yᵢ log xᵢ)',141,29);
 eq(s,'minₓ,ᵥ  f(x) + λR(v)     subject to x = v',233,29);
 eq(s,'xᵏ⁺¹ = arg minₓ≥₀ { f(x) + (ρ/2) ‖x − vᵏ + uᵏ‖₂² }',331,28);
 eq(s,'vᵏ⁺¹ = arg minᵥ { λR(v) + (ρ/2)‖v − xᵏ⁺¹ − uᵏ‖₂² }',418,27);
 eq(s,'uᵏ⁺¹ = uᵏ + xᵏ⁺¹ − vᵏ⁺¹,     σ² = λ/ρ',505,29);
 line(s,'Replace the v-step by D(xᵏ⁺¹ + uᵏ, σ). A general D may have no explicit R.',595,45,23);
}
{
 const s=slide('P4IP: closed-form Poisson denoising step',[1],
 'For denoising, H is the identity, so the likelihood update separates pixel by pixel. Define a as v minus u. Differentiating the scalar objective gives 1 minus y over x plus rho times x minus a. Multiplying by x gives a quadratic and selecting its nonnegative root gives the formula on the slide. If the observed count is zero, this reduces to max(a minus one over rho, zero). We then denoise x plus u and update u. The denoiser input is an intermediate ADMM image, so this does not assert that the original photon noise is Gaussian. The simple root is special to denoising. A blur operator couples pixels.');
 eq(s,'aᵢ = vᵢᵏ − uᵢᵏ',139,30);
 eq(s,'minₓᵢ≥₀ { xᵢ − yᵢ log xᵢ + (ρ/2)(xᵢ − aᵢ)² }',212,30);
 eq(s,'1 − yᵢ/xᵢ + ρ(xᵢ − aᵢ) = 0',301,30);
 eq(s,'xᵢᵏ⁺¹ = [ aᵢ − 1/ρ + √((aᵢ − 1/ρ)² + 4yᵢ/ρ) ] / 2',398,28);
 line(s,'For yᵢ = 0: xᵢᵏ⁺¹ = max(aᵢ − 1/ρ, 0).',502,58,27);
 line(s,'Repeat: Poisson update, Gaussian denoising, dual update.',575,45,27);
}
{
 const s=slide('What the supplied P4IP paper reports',[1],
 'These are published numbers, not results from our project. Table 1 of the supplied 2015 preprint reports average PSNR across eight images, without binning. P4IP is strongest among these three methods at peak 0.1 and 0.2. At peak 1, SPDA is higher. We therefore should not claim that P4IP wins at every level. Its useful feature for our work is the modular prior. The paper also studies multiple priors, which gives a direct precedent for testing an added wavelet prior.');
 line(s,'Average PSNR (dB), 8 images, without binning',145,42,26);
 table(s,[['Peak photons','Anscombe + BM3D','SPDA','P4IP'],['0.1','16.59','15.48','17.85'],['0.2','18.43','18.57','19.33'],['1.0','21.73','23.61','22.88']],213,[264,360,264,264],260,26);
 line(s,'P4IP leads at the two lowest peaks shown. SPDA leads at peak 1.',516,68,27);
 line(s,'Source: supplied arXiv v1, Table 1. These are published results, not project measurements.',606,42,19);
}
{
 const s=slide('Proposed direction A: change the P4IP prior',[1,3],
 'Our first direction keeps the exact Poisson update and changes the prior. With an orthonormal wavelet transform W, soft thresholding gives a concrete proximal denoiser. The threshold eta equals lambda over rho for an unweighted l1 wavelet penalty. This is a controlled baseline, and we would normally preserve or separately tune the approximation band. Next, learn a patch dictionary in the wavelet domain and use sparse patch reconstruction as the denoiser. To test whether wavelets complement BM3D, use the multiple-prior consensus split in the backup slide. BM3D already uses transform sparsity, so improvement must be measured rather than assumed. Freeze a learned dictionary during each reconstruction before experimenting with online updates.');
 label(s,'A1. Orthonormal wavelet shrinkage as the denoiser',145);
 eq(s,'D(r, η) = WᵀS(Wr, η),   S(c, η) = sign(c) max(|c| − η, 0)',209,28);
 line(s,'Keep P4IP’s likelihood update. Tune thresholds by wavelet subband.',287,63,25);
 label(s,'A2. Learn a dictionary for wavelet-domain image patches',368);
 eq(s,'WₚRⱼr ≈ Bαⱼ,     with sparse αⱼ and learned atoms in B',427,28);
 line(s,'Reconstruct and aggregate patches to define the replacement denoiser.',506,60,25);
 line(s,'Test BM3D + wavelet consensus as a separate variant. Gains remain a hypothesis.',577,66,25);
}
{
 const s=slide('Proposed direction B: explicit sparsity with ISTA/FISTA',[4,6],
 'A second direction makes the sparse objective explicit. Let z be the Anscombe-transformed image and let D be a fixed synthesis dictionary for z. We minimize a quadratic data term plus an l1 penalty on alpha. ISTA takes a gradient step and then applies soft thresholding. L is the squared spectral norm of D. FISTA adds momentum, with a better worst-case objective convergence rate for this convex problem. Recover D alpha in the transformed domain and use a suitable inverse Anscombe mapping. This inherits the approximation at low counts. For an orthonormal wavelet basis and pure denoising, the solution is already one soft-threshold step. Iteration is useful when the dictionary is redundant, or when the operator makes the problem coupled. Learning D jointly makes the outer problem nonconvex.');
 eq(s,'z = A(y),   minimize F(α) = ½ ‖Dα − z‖₂² + λ ‖α‖₁',145,29);
 eq(s,'∇f(α) = Dᵀ(Dα − z),     L = ‖D‖₂²',235,30);
 eq(s,'ISTA:  αᵏ⁺¹ = S(αᵏ − Dᵀ(Dαᵏ − z)/L, λ/L)',327,29);
 line(s,'FISTA adds momentum: objective gap O(1/k²), versus O(1/k) for ISTA.',431,70,26);
 line(s,'Use a redundant wavelet or learned dictionary, held fixed during sparse coding.',513,65,25);
 line(s,'Trade-off: simple sparse optimization, but approximate Poisson statistics after A.',595,45,24);
}
{
 const s=slide('Proposed evaluation and ablations',[],
 'Start by reproducing the baseline with controlled simulated counts. Normalize each clean image so its maximum is one and sample Poisson counts at the six peak levels shown. Use the same noise realizations across methods and separate images for tuning. Compare Anscombe-BM3D, P4IP-BM3D, and SPDA where feasible. Then change one component at a time: wavelet shrinkage, a fixed learned wavelet-patch dictionary, and multiple-prior fusion. Finally compare ISTA and FISTA on exactly the same fixed-dictionary objective and stopping tolerance. Report quality, runtime, residual behaviour, and sparsity. Treat binning as its own experiment because it trades resolution for count statistics. These are planned experiments, not claims of improvement.');
 eq(s,'x = p s,   yᵢ ∼ Poisson(xᵢ),   p ∈ {0.1, 0.2, 0.5, 1, 2, 4}',145,28);
 label(s,'Baselines',246);
 line(s,'Anscombe + BM3D, P4IP + BM3D, and SPDA where feasible.',292,62,26);
 label(s,'Controlled changes',371);
 line(s,'Wavelet prior, learned dictionary, BM3D + wavelet consensus, then ISTA/FISTA.',419,67,25);
 label(s,'Measurements',503);
 line(s,'PSNR / SSIM, runtime, coefficient sparsity, and convergence residuals.',550,47,26);
 line(s,'Same test images and noise seeds. Separate tuning set. Report binning separately.',613,38,21);
}
{
 const s=slide('Project question and next step',[1],
 'The key question is whether changing the representation improves the quality and computational cost at low photon counts. P4IP is a useful starting point because it keeps the exact observation model while making the denoiser replaceable. We will first reproduce P4IP-BM3D and test an interpretable wavelet prior, then a fixed learned dictionary. ISTA and FISTA give a separate explicit sparse formulation. The evidence will be paired quality and runtime comparisons across photon levels, with no assumed improvement.');
 text(s,'Can a wavelet or learned sparse prior improve the quality–runtime trade-off at low photon counts?',64,156,1152,154,36,true);
 line(s,'First: reproduce P4IP–BM3D with the exact Poisson data step.',364,66,28);
 line(s,'Then: replace or augment the prior and compare matched experiments.',451,68,28);
 line(s,'Alternative: solve an explicit sparse objective using ISTA/FISTA.',539,65,28);
}
{
 const s=slide('Backup: derivation of the Poisson proximal step',[1],
 'This is a derivation using rho for the augmented-Lagrangian penalty and lambda for the prior weight. The supplied paper uses lambda and beta, respectively. For positive counts, x must be strictly positive. For zero counts, the boundary is allowed. In floating-point implementations, let b=a−1/rho. If b<0 and y>0, the algebraically equivalent formula (2y/rho)/(sqrt(b²+4y/rho)−b) avoids cancellation. This numerical detail is a proposed implementation safeguard, not a measured result.',true);
 eq(s,'φ(x) = x − y log x + (ρ/2)(x − a)²,     x ≥ 0',145,29);
 eq(s,'φ′(x) = 1 − y/x + ρ(x − a)',233,30);
 eq(s,'ρx² + (1 − ρa)x − y = 0',321,32);
 eq(s,'x* = [ ρa − 1 + √((ρa − 1)² + 4ρy) ] / (2ρ)',411,29);
 eq(s,'φ″(x) = y/x² + ρ > 0     for x > 0',509,30);
 line(s,'The positive root is the unique minimizer for y > 0. Handle y = 0 at the boundary.',596,48,24);
}
{
 const s=slide('Backup: BM3D + wavelet consensus prior',[1],
 'This is a proposed two-prior variant following the multiple-prior split in the supplied P4IP paper. Let f include the nonnegative domain. Each auxiliary variable has its own denoising update and scaled dual. Summing the two quadratic terms gives an equivalent x-step with effective rho equal to rho1 plus rho2, and a equal to the weighted mean of vj minus uj. Thus the closed-form Poisson root is retained. The paper tested BM3D together with a simplified multiscale denoiser, not this specific wavelet design. Its Table 3 reports 20.38 dB for P4IP and 20.59 dB for M-P4IP at peak 0.2 with binning, which motivates testing but does not establish our result.',true);
 eq(s,'min  f(x) + λ₁R₁(v₁) + λ₂R₂(v₂),     x = v₁ = v₂',145,29);
 eq(s,'ρeff = ρ₁ + ρ₂,     a = [ρ₁(v₁ − u₁) + ρ₂(v₂ − u₂)] / ρeff',239,27);
 line(s,'Use the same Poisson root with a and ρeff.',326,49,26);
 eq(s,'v₁⁺ = BM3D(x⁺ + u₁; σ₁),     σ₁² = λ₁/ρ₁',397,28);
 eq(s,'v₂⁺ = Wᵀ S(W(x⁺ + u₂), λ₂/ρ₂)',474,30);
 eq(s,'uⱼ⁺ = uⱼ + x⁺ − vⱼ⁺,     j = 1, 2',550,29);
}
{
 const s=slide('Backup: learning the wavelet-domain dictionary',[3],
 'This slide defines the proposed dictionary denoiser, rather than claiming it is SPDA. R_j extracts a patch and W_p is an orthonormal wavelet transform on a patch. Fit B and sparse coefficients to transformed training patches with atom normalization to prevent scaling ambiguity. Reconstruct each patch with W_p transpose B alpha_j and average overlaps. The displayed w_j are positive aggregation weights. A wavelet transform alone does not increase expressivity if B is entirely free: B equals W_p times an arbitrary pixel dictionary. A meaningful wavelet enhancement therefore needs structure, such as keeping coarse coefficients separate and restricting learned atoms to selected detail subbands. Test those choices against a pixel-domain dictionary with the same atom count. Freeze B during the initial P4IP experiments.',true);
 eq(s,'cⱼ = WₚRⱼr',142,32);
 eq(s,'min over B, {αⱼ}:  ∑ⱼ [½ ‖cⱼ − Bαⱼ‖₂² + η ‖αⱼ‖₁]',221,29);
 eq(s,'subject to ‖bₗ‖₂ ≤ 1     for each dictionary atom bₗ',301,29);
 eq(s,'D(r) = (∑ⱼ wⱼRⱼᵀRⱼ)⁻¹ ∑ⱼ wⱼRⱼᵀWₚᵀBαⱼ',393,28);
 line(s,'Keep coarse coefficients separate. Learn detail-subband structure and test it.',488,71,26);
 line(s,'A free dictionary after an orthonormal wavelet transform is only a reparameterization. Structure must justify the enhancement.',579,71,23);
}
{
 const s=slide('Backup: complete FISTA iteration',[6],
 'For the fixed dictionary quadratic-plus-l1 objective, initialize alpha0, set q1=alpha0 and t1=1. At each iteration evaluate the gradient at qk, apply soft thresholding, update the momentum scalar, and extrapolate. L may be the squared spectral norm of D or selected by an appropriate backtracking scheme. The rates stated in the main talk apply to the convex objective with the needed smoothness and proximal assumptions. They do not promise a particular PSNR or faster wall-clock time in every case. The final line is our orthonormal special-case derivation, which explains why iteration is unnecessary for simple wavelet denoising.',true);
 eq(s,'q¹ = α⁰,     t₁ = 1,     L = ‖D‖₂²',142,30);
 eq(s,'αᵏ = S(qᵏ − Dᵀ(Dqᵏ − z)/L, λ/L)',225,30);
 eq(s,'tₖ₊₁ = [1 + √(1 + 4tₖ²)] / 2',309,31);
 eq(s,'qᵏ⁺¹ = αᵏ + [(tₖ − 1)/tₖ₊₁](αᵏ − αᵏ⁻¹)',395,30);
 label(s,'Special case: orthonormal wavelets, pure denoising',499);
 eq(s,'D = Wᵀ,  DᵀD = I     gives     α* = S(Dᵀz, λ)',558,29);
}
{
 const s=slide('Backup: exact Poisson sparsity and FISTA',[1,6],
 'This is our mathematical analysis of retaining the Poisson likelihood in a wavelet-regularized objective. For pure denoising, impose a small positive floor epsilon and let g contain both the wavelet l1 penalty and the domain constraint. The likelihood gradient has components 1 minus y_i over x_i, with diagonal Hessian y_i over x_i squared. Thus a Lipschitz bound exists on the restricted domain, but not globally as x approaches zero. A proximal-gradient method must respect that domain, and the proximal map of the sum of the l1 wavelet penalty and positivity indicator is generally not threshold-then-clip. One can use an inner solver for this proximal problem and a domain-safe method, or keep an ADMM split. The epsilon constraint changes the exact zero boundary and must be disclosed. This is why simply inserting BM3D into a FISTA update does not solve a defined sparse MAP objective.',true);
 eq(s,'minₓ  f(x) + g(x),     g(x) = λ‖Wx‖₁ + I{x≥ε}(x)',145,29);
 eq(s,'∇f(x) = 1 − y/x,     ∇²f(x) = diag(yᵢ/xᵢ²)',238,30);
 eq(s,'On x ≥ ε > 0, a valid bound is L = maxᵢ yᵢ / ε²',334,30);
 line(s,'Issue 1: the gradient is not globally Lipschitz near zero intensity.',439,62,26);
 line(s,'Issue 2: prox of λ‖Wx‖₁ + positivity is generally not “threshold, then clip.”',510,66,25);
 line(s,'Use a domain-safe method with an inner proximal solver, or retain ADMM splitting.',593,53,24);
}
{
 const s=slide('References: Poisson denoising and plug-and-play',[1,2,3,4],
 'The table in the main deck uses the supplied 2015 arXiv version of P4IP, which is distinct from the subsequently published journal version. Full source links are included in the notes for each relevant slide.',true);
 line(s,'[1] Rond, Giryes & Elad. Poisson Inverse Problems by the Plug-and-Play scheme. arXiv:1511.02500 (2015). JVCIR 41, 96–108 (2016).',145,92,25);
 line(s,'[2] Dabov, Foi, Katkovnik & Egiazarian. Image Denoising by Sparse 3-D Transform-Domain Collaborative Filtering. IEEE TIP 16(8), 2080–2095 (2007).',264,103,25);
 line(s,'[3] Giryes & Elad. Sparsity-Based Poisson Denoising With Dictionary Learning. IEEE TIP 23(12), 5055–5066 (2014). arXiv:1309.4306.',391,98,25);
 line(s,'[4] Mäkitalo & Foi. Optimal Inversion of the Anscombe Transformation in Low-Count Poisson Image Denoising. IEEE TIP 20(1), 99–109 (2011).',518,103,25);
}
{
 const s=slide('References: optimization and related sparse models',[5,6,7],
 'Poisson2Sparse is included as related work available in the project. It is a self-supervised neural sparse approach, whereas the proposed experiments in this talk start with classical wavelet and dictionary priors. No claim of novelty or superiority follows from reusing an established sparse prior. The contribution must be defined by a specific modification and a controlled evaluation.',true);
 line(s,'[5] Venkatakrishnan, Bouman & Wohlberg. Plug-and-Play Priors for Model Based Reconstruction. IEEE GlobalSIP, 945–948 (2013).',150,96,26);
 line(s,'[6] Beck & Teboulle. A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse Problems. SIAM J. Imaging Sciences 2(1), 183–202 (2009).',283,111,26);
 line(s,'[7] Ta, Aich, Gupta & Roy-Chowdhury. Poisson2Sparse: Self-Supervised Poisson Denoising From a Single Image (2022). arXiv:2206.01856.',432,109,26);
 line(s,'Full paper links and speaking notes are embedded in the slide notes.',598,43,23);
}

await fs.mkdir(path.join(build,'previews'),{recursive:true});
await (await PresentationFile.exportPptx(p)).save(path.join(build,'candidate.pptx'));
await fs.writeFile(path.join(build,'presentation.json'),JSON.stringify(p.toProto()));
const result=await finalizePresentation({workspaceDir:root,candidatePath:path.join(build,'candidate.pptx'),finalPath:path.join(root,'output','Poisson_Denoising_P4IP_Final.pptx'),pythonExecutable:python,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','3','--require-native-table-slide','9'],requiredNativeTableOwnerSlides:[3,9],fontPolicy:{basis:'design',families:['Arial','DejaVu Serif']},verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-v2.json')});
console.log(JSON.stringify(result));
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(build,'previews',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log(`Rendered ${p.slides.items.length} slides; main-slide timing ${times.reduce((a,b)=>a+b,0)} seconds.`);
