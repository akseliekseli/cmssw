import FWCore.ParameterSet.Config as cms

# -----------------------------------------------------------------------------
# Jet tagger training tables for the Phase2 L1 NanoAOD.
#
# Reproduces, in NanoAOD flat-table format, exactly the information stored by
# FastPUPPI/NtupleProducer/plugins/JetNTuplizer.cc (jetTuple_extended_5.root).
#
# Tables produced by L1JetTrainingTableProducer (module l1JetTrainTable):
#   L1JetTrain       one row per L1 jet  (columns named as JetNTuplizer branches)
#   L1JetTrainCand   one row per puppi candidate (column jetIdx -> parent jet row)
#   L1GenH           one row per last-copy Higgs (pt, mass); nL1GenH == ngenH
#   L1GenEvent       singleton: genHH_pt, genHH_mass, genHT, genHTall
# Offline content (jet_offline_* columns and the L1JetTrainOffCand table with
# the matched slimmedJetsPuppi constituents) is DISABLED here
# (doOfflineInfo=False); set it True to recover exactly the full
# JetNTuplizer content including offline matches.
#
# Upstream configuration mirrors FastPUPPI/NtupleProducer/python/runJetNtuple.py:
#   * dedicated clone of the NGJet producer with returnRawPt=True, maxJets=999,
#     minPt=0, maxEta=99 (training/full-coverage configuration).
#     NOTE doJEC is set to False even though runJetNtuple sets True: with
#     returnRawPt=True the producer never enters the JEC code path, so the two
#     settings yield an identical output collection, while doJEC=False avoids
#     opening the JEC corrector file jecs_20220308.root which is absent from
#     the release.
#   * dedicated clone of the BJet producer running on the training NGJets
#     (same settings as runJetNtuple.addBtagging()).
#   * genFlavourInfo (JetFlavourInfoMatching for ak4GenJetsNoNu), as in
#     runJetNtuple.addGenJetFlavourTable().
# The standard menu tables (e.g. L1puppiJetSC4NG) keep using the default
# producers and are not affected.
# -----------------------------------------------------------------------------

from L1Trigger.Phase2L1ParticleFlow.l1tSC4NGJetProducer_cfi import l1tSC4NGJetProducer
from L1Trigger.Phase2L1ParticleFlow.L1BJetProducer_cfi import L1BJetProducer

# training-configured NG jets (full coverage, raw pt) --------------------------------
l1tSC4NGJetTrainProducer = l1tSC4NGJetProducer.clone(
    jets = "l1tSC4PFL1PuppiExtendedEmulator",
    returnRawPt = True,
    doJEC = False,          # see NOTE above: inactive when returnRawPt=True
    maxJets = 999,
    minPt = 0.,
    maxEta = 99.,
)

# training b-tag scores on those jets ------------------------------------------------
l1tBJetProducerTrain = L1BJetProducer.clone(
    jets = ("l1tSC4NGJetTrainProducer", "l1tSC4NGJets"),
    useRawPt = True,
    maxJets = 500,
    vtx = ("l1tVertexFinderEmulator", "L1VerticesEmulation"),
)

# gen jet flavour info for ak4GenJetsNoNu (same as runJetNtuple.addGenJetFlavourTable,
# which also sets selectedHadronsAndPartons.partonMode = "Pythia8" on the process)
from PhysicsTools.JetMCAlgos.AK4PFJetsMCFlavourInfos_cfi import ak4JetFlavourInfos
from PhysicsTools.JetMCAlgos.HadronAndPartonSelector_cfi import selectedHadronsAndPartons as _shp
selectedHadronsAndPartons = _shp.clone(partonMode = "Pythia8")
genFlavourInfo = ak4JetFlavourInfos.clone(jets = "ak4GenJetsNoNu")

# the table producer itself ----------------------------------------------------------
l1JetTrainTable = cms.EDProducer("L1JetTrainingTableProducer",
    genJets           = cms.InputTag("ak4GenJetsNoNu"),
    genParticles      = cms.InputTag("genParticles"),
    scPuppiJets       = cms.InputTag("l1tSC4NGJetTrainProducer", "l1tSC4NGJets"),
    scPuppiJetsCorr   = cms.InputTag("l1tSC4PFL1PuppiCorrectedEmulator"),
    nnTaus            = cms.InputTag("l1tNNTauProducerPuppi", "L1PFTausNN"),
    electrons         = cms.InputTag("l1tLayer2EG", "L1CtTkElectron"),
    # "prompt" is the in-job producer instance label (Phase2L1TGMTSAMuonGhost-
    # Cleaner makes "prompt"/"displaced"); JetNTuplizer-era configs read
    # "promptSAMuons" from precomputed file products (same objects).
    muons             = cms.InputTag("l1tSAMuonsGmt", "prompt"),
    genJetsFlavour    = cms.InputTag("genFlavourInfo"),
    vtx               = cms.InputTag("l1tVertexFinderEmulator", "L1VerticesEmulation"),
    bjetIDs           = cms.InputTag("l1tBJetProducerTrain", "L1PFBJets"),
    offlineJets       = cms.InputTag("slimmedJetsPuppi"),
    offlinePVs        = cms.InputTag("offlineSlimmedPrimaryVertices"),
    # OFF: keep only L1JetTrain + L1JetTrainCand (plus L1GenH/L1GenEvent).
    # With False, neither the jet_offline_* columns nor the L1JetTrainOffCand
    # table are produced (this was ~40% of the training tables' size).
    doOfflineInfo     = cms.bool(False),
)

l1tJetTrainingTask = cms.Task(
    l1tSC4NGJetTrainProducer,
    l1tBJetProducerTrain,
    selectedHadronsAndPartons,
    genFlavourInfo,
    l1JetTrainTable,
)

def addL1JetTrainingTables(process):
    """Add the jet tagger training tables to the Phase2 L1 NanoAOD production.

    Mirrors the settings of FastPUPPI/NtupleProducer/python/runJetNtuple.py:
    the NNTau cap is raised to 500 taus/event from the menu default of 5, to
    keep jet<->tau matching identical to the JetNTuplizer job.
    """
    process.l1tPh2NanoTask.add(l1tJetTrainingTask)
    if hasattr(process, "l1tNNTauProducerPuppi"):
        process.l1tNNTauProducerPuppi.maxtaus = cms.int32(500)
    return process


def addSC8JetTrainingTables(process):
    """Add FastPUPPI extended SC8 training jets alongside the existing tables."""
    process.sc8TrainSeeds = process.l1tSC4PFL1PuppiExtendedEmulator.clone(
        coneSize=0.8, wideConeJet=True,
    )
    process.sc8TrainNGJets = process.l1tSC4NGJetTrainProducer.clone(jets="sc8TrainSeeds")
    jets = cms.InputTag("sc8TrainNGJets", "l1tSC4NGJets")
    process.sc8TrainBTags = process.l1tBJetProducerTrain.clone(jets=jets)
    # Index in this list is the stored truth code. Append future labels at the end.
    # The full decoding is also written into the ROOT branch title.
    process.sc8TrainTable = process.l1JetTrainTable.clone(
        tableName=cms.string("L1JetTrainSC8"),
        writeGenTables=cms.bool(False),
        scPuppiJets=jets,
        scPuppiJetsCorr="l1tSC8PFL1PuppiCorrectedEmulator",
        bjetIDs=("sc8TrainBTags", "L1PFBJets"),
        sc8Labels=cms.vstring(
            "QCD_others", "H_bb", "H_cc", "H_qq",
            "H_gg", "Cust_btaue", "Cust_btauh", "Cust_btaum",
            "Cust_ctaue", "Cust_ctauh", "Cust_ctaum", "Cust_gtaue",
            "Cust_gtauh", "Cust_gtaum", "Cust_qtaue", "Cust_qtauh",
            "Cust_qtaum", "Cust_staue", "Cust_stauh", "Cust_staum",
            "Cust_taue", "Cust_tauh", "Cust_taum", "Data",
            "H_HVext_aab", "H_HVext_aabb", "H_HVext_aabc", "H_HVext_aabq",
            "H_HVext_aac", "H_HVext_aacc", "H_HVext_aacq", "H_HVext_aacs",
            "H_HVext_aae", "H_HVext_aaee", "H_HVext_aag", "H_HVext_aagg",
            "H_HVext_aam", "H_HVext_aamm", "H_HVext_aaq", "H_HVext_aaqq",
            "H_HVext_aas", "H_HVext_aasq", "H_HVext_aass", "H_HVext_aataue",
            "H_HVext_aatauh", "H_HVext_aatauhtaue", "H_HVext_aatauhtauh", "H_HVext_aatauhtaum",
            "H_HVext_aataum", "H_HVext_abb", "H_HVext_abc", "H_HVext_abq",
            "H_HVext_acc", "H_HVext_acq", "H_HVext_acs", "H_HVext_aee",
            "H_HVext_agg", "H_HVext_amm", "H_HVext_aqq", "H_HVext_asq",
            "H_HVext_ass", "H_HVext_atauhtaue", "H_HVext_atauhtauh", "H_HVext_atauhtaum",
            "H_WW_csc", "H_WW_cscs", "H_WW_csev", "H_WW_csmv",
            "H_WW_csq", "H_WW_csqq", "H_WW_css", "H_WW_cstauev",
            "H_WW_cstauhv", "H_WW_cstaumv", "H_WW_qqc", "H_WW_qqev",
            "H_WW_qqmv", "H_WW_qqq", "H_WW_qqqq", "H_WW_qqs",
            "H_WW_qqtauev", "H_WW_qqtauhv", "H_WW_qqtaumv", "H_ZZ_bbb",
            "H_ZZ_bbbb", "H_ZZ_bbc", "H_ZZ_bbcc", "H_ZZ_bbe",
            "H_ZZ_bbee", "H_ZZ_bbm", "H_ZZ_bbmm", "H_ZZ_bbq",
            "H_ZZ_bbqq", "H_ZZ_bbs", "H_ZZ_bbss", "H_ZZ_bbtauhtaue",
            "H_ZZ_bbtauhtauh", "H_ZZ_bbtauhtaum", "H_ZZ_bee", "H_ZZ_bmm",
            "H_ZZ_btauhtaue", "H_ZZ_btauhtauh", "H_ZZ_btauhtaum", "H_ZZ_ccb",
            "H_ZZ_ccc", "H_ZZ_cccc", "H_ZZ_cce", "H_ZZ_ccee",
            "H_ZZ_ccm", "H_ZZ_ccmm", "H_ZZ_ccq", "H_ZZ_ccqq",
            "H_ZZ_ccs", "H_ZZ_ccss", "H_ZZ_cctauhtaue", "H_ZZ_cctauhtauh",
            "H_ZZ_cctauhtaum", "H_ZZ_cee", "H_ZZ_cmm", "H_ZZ_ctauhtaue",
            "H_ZZ_ctauhtauh", "H_ZZ_ctauhtaum", "H_ZZ_qee", "H_ZZ_qmm",
            "H_ZZ_qqb", "H_ZZ_qqc", "H_ZZ_qqe", "H_ZZ_qqee",
            "H_ZZ_qqm", "H_ZZ_qqmm", "H_ZZ_qqq", "H_ZZ_qqqq",
            "H_ZZ_qqs", "H_ZZ_qqtauhtaue", "H_ZZ_qqtauhtauh", "H_ZZ_qqtauhtaum",
            "H_ZZ_qtauhtaue", "H_ZZ_qtauhtauh", "H_ZZ_qtauhtaum", "H_ZZ_see",
            "H_ZZ_smm", "H_ZZ_ssb", "H_ZZ_ssc", "H_ZZ_sse",
            "H_ZZ_ssee", "H_ZZ_ssm", "H_ZZ_ssmm", "H_ZZ_ssq",
            "H_ZZ_ssqq", "H_ZZ_sss", "H_ZZ_ssss", "H_ZZ_sstauhtaue",
            "H_ZZ_sstauhtauh", "H_ZZ_sstauhtaum", "H_ZZ_stauhtaue", "H_ZZ_stauhtauh",
            "H_ZZ_stauhtaum", "H_bc", "H_bs", "H_cs",
            "H_ee", "H_mm", "H_ss", "H_tauhtaue",
            "H_tauhtauh", "H_tauhtaum", "Hext_aa", "Invalid",
            "QCD_b", "QCD_bb", "QCD_c", "QCD_cc",
            "Top_Wcs", "Top_Wev", "Top_Wmv", "Top_Wqq",
            "Top_Wtauev", "Top_Wtauhv", "Top_Wtaumv", "Top_bWc",
            "Top_bWcs", "Top_bWev", "Top_bWmv", "Top_bWq",
            "Top_bWqq", "Top_bWs", "Top_bWtauev", "Top_bWtauhv",
            "Top_bWtaumv", "W_cs", "W_ev", "W_mv",
            "W_qq", "W_tauev", "W_tauhv", "W_taumv",
            "Z_bb", "Z_cc", "Z_qq", "Z_ss",
        ),
    )
    process.l1tPh2NanoTask.add(process.sc8TrainSeeds, process.sc8TrainNGJets,
                               process.sc8TrainBTags, process.sc8TrainTable)
    return process
