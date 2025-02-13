// -*- C++ -*-
#include "Rivet/Analysis.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/FastJets.hh"
#include "Rivet/Projections/VetoedFinalState.hh"
#include "Rivet/Projections/IdentifiedFinalState.hh"

namespace Rivet
{

  /// @brief Add a short analysis description here
  class MC_VBF_HH : public Analysis
  {
  public:
    /// Constructor
    RIVET_DEFAULT_ANALYSIS_CTOR(MC_VBF_HH);

    /// @name Analysis methods
    /// @{

    /// Book histograms and initialise projections before the run
    void init()
    {
      IdentifiedFinalState ifs(Cuts::abseta < 10.0 && Cuts::pT > 0 * GeV);
      ifs.acceptId(25);
      declare(ifs, "IFS");
      VetoedFinalState vfs;
      vfs.addVetoPairId(25);
      FastJets jetpro(vfs, JetAlg::ANTIKT, 0.4);
      declare(jetpro, "Jets");

      const double sqrts = sqrtS() ? sqrtS() : 14 * TeV;

      const double pTmax = sqrts / GeV / 4.0;
      book(_h_pT_jet1, "jet_pT_1", logspace(50, 20.0, pTmax));
      book(_h_pT_jet2, "jet_pT_2", logspace(50, 20.0, pTmax));
      book(_h_pT_jet3, "jet_pT_3", logspace(50, 20.0, pTmax));

      book(_h_eta_jet1, "jet_eta_1", 25, -5.0, 5.0);
      book(_h_eta_jet2, "jet_eta_2", 25, -5.0, 5.0);
      book(_h_eta_jet3, "jet_eta_3", 25, -5.0, 5.0);

      book(_h_rap_jet1, "jet_y_1", 25, -5.0, 5.0);
      book(_h_rap_jet2, "jet_y_2", 25, -5.0, 5.0);
      book(_h_rap_jet3, "jet_y_3", 25, -5.0, 5.0);

      book(_h_absdeta_jets12, "jets_absdeta_12", 10, 3.5, 7.5);
      book(_h_dphi_jets12, "jets_dphi_12", 25, 0.0, M_PI);
      book(_h_dR_jets12, "jets_dR_12", 25, 4.0, 8.0);
      book(_h_absdeta_jets13, "jets_absdeta_13", 10, 3.5, 7.5);
      book(_h_dphi_jets13, "jets_dphi_13", 25, 0.0, M_PI);
      book(_h_dR_jets13, "jets_dR_13", 25, 4.0, 8.0);
      book(_h_absdeta_jets23, "jets_absdeta_23", 10, 3.5, 7.5);
      book(_h_dphi_jets23, "jets_dphi_23", 25, 0.0, M_PI);
      book(_h_dR_jets23, "jets_dR_23", 25, 4.0, 8.0);

      book(_h_jet_HT, "jet_HT", logspace(50, 30, sqrts / GeV / 2.0));
      book(_h_mjj_jets12, "jets_mjj12", 40, 0.0, sqrts / GeV / 2.0);
      book(_h_mjj_jets13, "jets_mjj13", 40, 0.0, sqrts / GeV / 2.0);
      book(_h_mjj_jets23, "jets_mjj23", 40, 0.0, sqrts / GeV / 2.0);

      book(_h_HH_mass, "HH_mass", 100, 200, 4000.0);
      book(_h_HH_dR, "HH_dR", 25, 0.5, 10.0);
      book(_h_HH_dPhi, "HH_dPhi", 32, 0, 3.2);
      book(_h_HH_deta, "HH_deta", 25, -5, 5);
      book(_h_H_pT, "H_pT", 30, 0, 2000.0);
      book(_h_HH_pT, "HH_pT", 30, 0, 2000.0);
      book(_h_H_pT1, "H_pT1", 30, 0, 2000.0);
      book(_h_H_pT2, "H_pT2", 30, 0, 2000.0);
      book(_h_H_eta, "H_eta", 25, -5.0, 5.0);
      book(_h_H_eta1, "H_eta1", 25, -5.0, 5.0);
      book(_h_H_eta2, "H_eta2", 25, -5.0, 5.0);
      book(_h_H_phi, "H_phi", 25, 0.0, TWOPI);
      book(_h_H_jet1_deta, "H_jet1_deta", 25, 0, 5.0);
      book(_h_H_jet1_dR, "H_jet1_dR", 25, 0.5, 7.0);
      book(_h_H_jet2_deta, "H_jet2_deta", 25, 0, 5.0);
      book(_h_H_jet2_dR, "H_jet2_dR", 25, 0.5, 7.0);
      book(_h_H_jet3_deta, "H_jet3_deta", 25, 0, 5.0);
      book(_h_H_jet3_dR, "H_jet3_dR", 25, 0.5, 7.0);
    }

    /// Perform the per-event analysis
    void analyze(const Event &event)
    {

      const IdentifiedFinalState &ifs = apply<IdentifiedFinalState>(event, "IFS");
      Particles allp = ifs.particlesByPt();
      if (allp.empty())
        vetoEvent;

      FourMomentum hmom = allp[0].momentum();
      if (allp.size() > 1)
      {
        FourMomentum hmom2(allp[1].momentum());
        _h_HH_dR->fill(deltaR(hmom, hmom2));
        _h_HH_dPhi->fill(deltaPhi(hmom, hmom2));
        _h_HH_deta->fill(hmom.eta() - hmom2.eta());
        _h_HH_pT->fill((hmom + hmom2).pT());
        _h_HH_mass->fill((hmom + hmom2).mass());

        if (hmom.pT() > hmom2.pT())
        {
          _h_H_pT1->fill(hmom.pT());
          _h_H_eta1->fill(hmom.eta());
          _h_H_pT2->fill(hmom2.pT());
          _h_H_eta2->fill(hmom2.eta());
        }
        else
        {
          _h_H_pT1->fill(hmom2.pT());
          _h_H_eta1->fill(hmom2.eta());
          _h_H_pT2->fill(hmom.pT());
          _h_H_eta2->fill(hmom.eta());
        }
      }
      _h_H_pT->fill(hmom.pT());
      _h_H_eta->fill(hmom.eta());
      _h_H_phi->fill(hmom.azimuthalAngle());

      Jets jets = apply<FastJets>(event, "Jets").jetsByPt(Cuts::pT > 20 * GeV);
      if (!jets.empty())
      {
        _h_H_jet1_deta->fill(deltaEta(hmom, jets[0]));
        _h_H_jet1_dR->fill(deltaR(hmom, jets[0]));

        _h_pT_jet1->fill(jets[0].pT()/GeV);
        _h_eta_jet1->fill(jets[0].eta());
        _h_rap_jet1->fill(jets[0].rapidity());
        if (jets.size() > 1) {
          _h_pT_jet2->fill(jets[1].pT()/GeV);
          _h_eta_jet2->fill(jets[1].eta());
          _h_rap_jet2->fill(jets[1].rapidity());

          _h_H_jet2_deta->fill(deltaEta(hmom, jets[1]));
          _h_H_jet2_dR->fill(deltaR(hmom, jets[1]));

          _h_absdeta_jets12->fill(abs(jets[0].eta()-jets[1].eta()));
          _h_dphi_jets12->fill(deltaPhi(jets[0].momentum(),jets[1].momentum()));
          _h_dR_jets12->fill(deltaR(jets[0].momentum(), jets[1].momentum()));

          _h_mjj_jets12->fill((jets[0].momentum() + jets[1].momentum()).mass());
        }

        if (jets.size() > 2) {
          _h_pT_jet3->fill(jets[2].pT()/GeV);
          _h_eta_jet3->fill(jets[2].eta());
          _h_rap_jet3->fill(jets[2].rapidity());

          _h_H_jet3_deta->fill(deltaEta(hmom, jets[2]));
          _h_H_jet3_dR->fill(deltaR(hmom, jets[2]));

          _h_absdeta_jets13->fill(abs(jets[0].eta()-jets[2].eta()));
          _h_dphi_jets13->fill(deltaPhi(jets[0].momentum(),jets[2].momentum()));
          _h_dR_jets13->fill(deltaR(jets[0].momentum(), jets[2].momentum()));

          _h_absdeta_jets23->fill(abs(jets[1].eta()-jets[2].eta()));
          _h_dphi_jets23->fill(deltaPhi(jets[1].momentum(),jets[2].momentum()));
          _h_dR_jets23->fill(deltaR(jets[1].momentum(), jets[2].momentum()));

          _h_mjj_jets13->fill((jets[0].momentum() + jets[2].momentum()).mass());
          _h_mjj_jets23->fill((jets[1].momentum() + jets[2].momentum()).mass());
        }

        double HT = 0.0;
        for (const Jet& jet : jets) {
          HT += jet.pT();
        }
        _h_jet_HT->fill(HT);


      }
    }

    /// Normalise histograms etc., after the run
    void finalize()
    {
      const double scaling = crossSection() / picobarn / sumOfWeights();

      scale(_h_HH_mass, scaling);
      scale(_h_HH_dR, scaling);
      scale(_h_HH_deta, scaling);
      scale(_h_HH_dPhi, scaling);
      scale(_h_H_pT, scaling);
      scale(_h_H_pT1, scaling);
      scale(_h_H_pT2, scaling);
      scale(_h_HH_pT, scaling);
      scale(_h_H_eta, scaling);
      scale(_h_H_eta1, scaling);
      scale(_h_H_eta2, scaling);
      scale(_h_H_phi, scaling);
      scale(_h_H_jet1_deta, scaling);
      scale(_h_H_jet1_dR, scaling);
      scale(_h_H_jet2_deta, scaling);
      scale(_h_H_jet2_dR, scaling);
      scale(_h_H_jet3_deta, scaling);
      scale(_h_H_jet3_dR, scaling);

      scale(_h_pT_jet1, scaling);
      scale(_h_pT_jet2, scaling);
      scale(_h_pT_jet3, scaling);
      scale(_h_eta_jet1, scaling);
      scale(_h_eta_jet2, scaling);
      scale(_h_eta_jet3, scaling);
      scale(_h_rap_jet1, scaling);
      scale(_h_rap_jet2, scaling);
      scale(_h_rap_jet3, scaling);
      scale(_h_absdeta_jets12, scaling);
      scale(_h_dphi_jets12, scaling);
      scale(_h_dR_jets12, scaling);
      scale(_h_absdeta_jets13, scaling);
      scale(_h_dphi_jets13, scaling);
      scale(_h_dR_jets13, scaling);
      scale(_h_absdeta_jets23, scaling);
      scale(_h_dphi_jets23, scaling);
      scale(_h_dR_jets23, scaling);
      scale(_h_jet_HT, scaling);
      scale(_h_mjj_jets12, scaling);
      scale(_h_mjj_jets13, scaling);
      scale(_h_mjj_jets23, scaling);
    }

    /// @}

    /// @name Histograms
    /// @{
    Histo1DPtr _h_HH_mass, _h_HH_pT, _h_HH_dR, _h_HH_deta, _h_HH_dPhi;
    Histo1DPtr _h_H_pT, _h_H_pT1, _h_H_pT2, _h_H_eta, _h_H_eta1, _h_H_eta2, _h_H_phi;
    Histo1DPtr _h_H_jet1_deta, _h_H_jet1_dR, _h_H_jet2_deta, _h_H_jet2_dR, _h_H_jet3_deta, _h_H_jet3_dR;
    Histo1DPtr _h_pT_jet1, _h_eta_jet1, _h_rap_jet1;
    Histo1DPtr _h_pT_jet2, _h_eta_jet2, _h_rap_jet2;
    Histo1DPtr _h_pT_jet3, _h_eta_jet3, _h_rap_jet3;
    Histo1DPtr _h_jet_HT;
    Histo1DPtr _h_absdeta_jets12, _h_dphi_jets12, _h_dR_jets12, _h_mjj_jets12;
    Histo1DPtr _h_absdeta_jets13, _h_dphi_jets13, _h_dR_jets13, _h_mjj_jets13;
    Histo1DPtr _h_absdeta_jets23, _h_dphi_jets23, _h_dR_jets23, _h_mjj_jets23;
    /// @}
  };

  RIVET_DECLARE_PLUGIN(MC_VBF_HH);

}
