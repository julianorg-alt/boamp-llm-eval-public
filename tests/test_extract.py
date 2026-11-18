from boamp_eval.extract import contact_names, extract_truth


def _joue(lots=2):
    def lot(i, name):
        return {
            "cbc:ID": {"@schemeName": "Lot", "#text": f"LOT-000{i}"},
            "cac:ProcurementProject": {"cbc:Name": {"@languageID": "FRA", "#text": name}},
            "cac:TenderingProcess": {
                "cac:TenderSubmissionDeadlinePeriod": {
                    "cbc:EndDate": "2026-10-21+02:00",
                    "cbc:EndTime": "16:00:00+02:00",
                }
            },
            "cac:TenderingTerms": {
                "cac:AwardingTerms": {
                    "cac:AwardingCriterion": {
                        "cac:SubordinateAwardingCriterion": [
                            {
                                "cbc:AwardingCriterionTypeCode": {"#text": "quality"},
                                "cbc:Description": {"#text": "Valeur technique"},
                                "ext:UBLExtensions": {
                                    "ext:UBLExtension": {
                                        "ext:ExtensionContent": {
                                            "efext:EformsExtension": {
                                                "efac:AwardCriterionParameter": {
                                                    "efbc:ParameterCode": {"#text": "poi-exa"},
                                                    "efbc:ParameterNumeric": "60",
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                            {
                                "cbc:AwardingCriterionTypeCode": {"#text": "price"},
                                "cbc:Description": {"#text": "Prix"},
                                "ext:UBLExtensions": {
                                    "ext:UBLExtension": {
                                        "ext:ExtensionContent": {
                                            "efext:EformsExtension": {
                                                "efac:AwardCriterionParameter": {
                                                    "efbc:ParameterCode": {"#text": "poi-exa"},
                                                    "efbc:ParameterNumeric": "40",
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                        ]
                    }
                }
            },
        }

    lots_ = [lot(1, "Lot A"), lot(2, "Lot B")][:lots]
    return {
        "EFORMS": {
            "ContractNotice": {
                "ext:UBLExtensions": {
                    "ext:UBLExtension": {
                        "ext:ExtensionContent": {
                            "efext:EformsExtension": {
                                "efac:Organizations": {
                                    "efac:Organization": [
                                        {
                                            "efac:Company": {
                                                "cac:PartyIdentification": {
                                                    "cbc:ID": {"#text": "ORG-0001"}
                                                },
                                                "cac:PartyName": {
                                                    "cbc:Name": {"#text": "Commune d'Hyères"}
                                                },
                                                "cac:Contact": {
                                                    "cbc:Name": "Jean Martin",
                                                    "cbc:ElectronicMail": "a@b.fr",
                                                },
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    }
                },
                "cac:ContractingParty": {
                    "cac:Party": {"cac:PartyIdentification": {"cbc:ID": "ORG-0001"}}
                },
                "cac:TenderingProcess": {"cbc:ProcedureCode": {"#text": "open"}},
                "cac:ProcurementProject": {
                    "cbc:Name": {"#text": "Travaux de voirie"},
                    "cac:MainCommodityClassification": {
                        "cbc:ItemClassificationCode": {"#text": "45233140"}
                    },
                    "cac:AdditionalCommodityClassification": {
                        "cbc:ItemClassificationCode": {"#text": "45233141"}
                    },
                    "cac:RequestedTenderTotal": {
                        "cbc:EstimatedOverallContractAmount": {
                            "@currencyID": "EUR",
                            "#text": "139460",
                        }
                    },
                    "cac:RealizedLocation": {
                        "cac:Address": {"cbc:CountrySubentityCode": {"#text": "FRL05"}}
                    },
                },
                "cac:ProcurementProjectLot": lots_ if lots > 1 else lots_[0],
            }
        }
    }


def test_joue_full():
    t = extract_truth("JOUE", _joue())
    assert t["acheteur"] == "Commune d'Hyères"
    assert t["objet"] == "Travaux de voirie"
    assert t["cpv"] == ["45233140", "45233141"]
    assert t["lots"] == [{"id": "LOT-0001", "titre": "Lot A"}, {"id": "LOT-0002", "titre": "Lot B"}]
    assert t["montant_estime"] == {"valeur": 139460.0, "devise": "EUR"}
    assert t["procedure"] == "open"
    assert t["date_limite"] == "2026-10-21T16:00:00+02:00"
    assert t["criteres"] == [
        {"type": "quality", "libelle": "Valeur technique", "poids": 60.0},
        {"type": "price", "libelle": "Prix", "poids": 40.0},
    ]
    assert t["lieu"] == "FRL05"


def test_joue_single_lot_is_not_lots():
    assert "lots" not in extract_truth("JOUE", _joue(lots=1))


def test_joue_contact_names():
    assert contact_names("JOUE", _joue()) == ["Jean Martin"]


FNS = {
    "FNSimple": {
        "organisme": {"nomOfficiel": "Mairie de Testville"},
        "initial": {
            "communication": {"nomContact": "Marc EXEMPLE, Maire de Testville"},
            "procedure": {
                "procedureAdapteeO": "",
                "dateReceptionOffres": "2026-11-06T12:00:00.000+01:00",
                "criteresAttrib": "Critères énoncés dans les documents",
            },
            "natureMarche": {
                "intitule": "Travaux voie romaine",
                "codeCPV": {"objetPrincipal": {"classPrincipale": "45233140"}},
                "lieuExecution": "(29) Finistère",
                "valeurEstimee": {"@devise": "EUR", "valeur": "200000"},
            },
            "lots": {"lot": [{"description": "Terrassement"}, {"description": "Mobilier"}]},
        },
    }
}


def test_fns():
    t = extract_truth("FNS", FNS)
    assert t == {
        "acheteur": "Mairie de Testville",
        "objet": "Travaux voie romaine",
        "cpv": ["45233140"],
        "lots": [{"id": "1", "titre": "Terrassement"}, {"id": "2", "titre": "Mobilier"}],
        "montant_estime": {"valeur": 200000.0, "devise": "EUR"},
        "procedure": "adapted-open",
        "date_limite": "2026-11-06T12:00:00+01:00",
        "lieu": "(29) Finistère",
    }
    assert contact_names("FNS", FNS) == ["Marc EXEMPLE, Maire de Testville"]


def test_fns_fourchette_has_no_amount():
    d = {
        "FNSimple": {
            "organisme": {"nomOfficiel": "X"},
            "initial": {
                "natureMarche": {
                    "intitule": "Y",
                    "valeurEstimee": {"@devise": "EUR", "fourchette": ""},
                }
            },
        }
    }
    assert "montant_estime" not in extract_truth("FNS", d)


MAPA = {
    "MAPA": {
        "organisme": {
            "acheteurPublic": "COMMUNE DE MIEUSSY",
            "correspondantPRM": {"nom": "TESTNOM", "pren": "Xavier"},
        },
        "initial": {
            "description": {
                "objet": "Site internet",
                "lieuExecutionLivraison": {"voie": {"nomvoie": "FRK28 - Haute-Savoie"}},
            },
            "procedure": {"procedureAdaptee": ""},
            "delais": {"receptionOffres": "2026-11-20T12:00:00"},
            "criteres": {
                "criterePondere": [
                    {"critere": "Prix", "criterePCT": "40"},
                    {"critere": "Valeur technique", "criterePCT": "60"},
                ]
            },
            "lots": {
                "lot": [
                    {"numLot": "1", "description": "CVC"},
                    {"numLot": "2", "description": "Plâtrerie"},
                ]
            },
        },
    }
}


def test_mapa():
    t = extract_truth("MAPA", MAPA)
    assert t["acheteur"] == "COMMUNE DE MIEUSSY"
    assert "cpv" not in t and "montant_estime" not in t
    assert t["procedure"] == "adapted"
    assert t["date_limite"] == "2026-11-20T12:00:00"
    assert t["criteres"] == [
        {"type": None, "libelle": "Prix", "poids": 40.0},
        {"type": None, "libelle": "Valeur technique", "poids": 60.0},
    ]
    assert t["lots"][1] == {"id": "2", "titre": "Plâtrerie"}
    assert t["lieu"] == "FRK28 - Haute-Savoie"
    assert contact_names("MAPA", MAPA) == ["TESTNOM", "Xavier"]


def test_malformed_returns_empty():
    assert extract_truth("JOUE", {"foo": 1}) == {}
    assert extract_truth("MAPA", {}) == {}
