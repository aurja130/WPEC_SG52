"""SG52 pseudo quantity-ID reference tables for PFNS and mubar data.

These identifiers are specific to the WPEC SG52 processed covariance dataset.
They are NOT standard ENDF-6 MT numbers.

PFNS
----
The prompt fission neutron spectrum (PFNS, chi) is fundamentally MF=5/MT=18
data.  SG52 uses ten incident-neutron energy groups.  Each pseudo-ID below
selects one incident-energy group; the corresponding ``*-xs.txt`` file then
contains 51 values over the common 51-group OUTGOING-neutron energy structure.

Mubar
-----
Mubar is the average cosine of the elastic-scattering angle, based on the
derived MT=251 quantity.  SG52 represents it at ten incident-neutron energy
ranges.  Each pseudo-ID below selects one such range; the corresponding
``*-xs.txt`` file contains one scalar mubar value.

Energy bounds are stored in MeV.
"""

from typing import TypedDict


class PFNSMetadata(TypedDict):
    quantity: str
    base_mf: int
    base_mt: int
    incident_group: int
    incident_energy_lower_mev: float
    incident_energy_upper_mev: float
    description: str


class MubarMetadata(TypedDict):
    quantity: str
    base_mt: int
    incident_group: int
    incident_energy_lower_mev: float
    incident_energy_upper_mev: float
    description: str

PFNS_PSEUDO_IDS: dict[int, PFNSMetadata] = {
    1018: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 0,
        "incident_energy_lower_mev": 1.00e-11,
        "incident_energy_upper_mev": 6.41e-7,
        "description": "Prompt fission neutron spectrum for incident-energy group 0; file values span 51 outgoing-energy groups.",
    },
    1118: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 1,
        "incident_energy_lower_mev": 6.41e-7,
        "incident_energy_upper_mev": 5.00e-1,
        "description": "Prompt fission neutron spectrum for incident-energy group 1; file values span 51 outgoing-energy groups.",
    },
    1218: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 2,
        "incident_energy_lower_mev": 5.00e-1,
        "incident_energy_upper_mev": 1.35,
        "description": "Prompt fission neutron spectrum for incident-energy group 2; file values span 51 outgoing-energy groups.",
    },
    1318: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 3,
        "incident_energy_lower_mev": 1.35,
        "incident_energy_upper_mev": 5.35,
        "description": "Prompt fission neutron spectrum for incident-energy group 3; file values span 51 outgoing-energy groups.",
    },
    1418: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 4,
        "incident_energy_lower_mev": 5.35,
        "incident_energy_upper_mev": 6.07,
        "description": "Prompt fission neutron spectrum for incident-energy group 4; file values span 51 outgoing-energy groups.",
    },
    1518: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 5,
        "incident_energy_lower_mev": 6.07,
        "incident_energy_upper_mev": 10.0,
        "description": "Prompt fission neutron spectrum for incident-energy group 5; file values span 51 outgoing-energy groups.",
    },
    1618: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 6,
        "incident_energy_lower_mev": 10.0,
        "incident_energy_upper_mev": 13.0,
        "description": "Prompt fission neutron spectrum for incident-energy group 6; file values span 51 outgoing-energy groups.",
    },
    1718: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 7,
        "incident_energy_lower_mev": 13.0,
        "incident_energy_upper_mev": 14.0,
        "description": "Prompt fission neutron spectrum for incident-energy group 7; file values span 51 outgoing-energy groups.",
    },
    1818: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 8,
        "incident_energy_lower_mev": 14.0,
        "incident_energy_upper_mev": 15.0,
        "description": "Prompt fission neutron spectrum for incident-energy group 8; file values span 51 outgoing-energy groups.",
    },
    1918: {
        "quantity": "PFNS",
        "base_mf": 5,
        "base_mt": 18,
        "incident_group": 9,
        "incident_energy_lower_mev": 15.0,
        "incident_energy_upper_mev": 20.0,
        "description": "Prompt fission neutron spectrum for incident-energy group 9; file values span 51 outgoing-energy groups.",
    },
}


MUBAR_PSEUDO_IDS: dict[int, MubarMetadata] = {
    251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 0,
        "incident_energy_lower_mev": 1.00e-11,
        "incident_energy_upper_mev": 6.41e-7,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 0; file contains one scalar value.",
    },
    1251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 1,
        "incident_energy_lower_mev": 6.41e-7,
        "incident_energy_upper_mev": 5.00e-1,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 1; file contains one scalar value.",
    },
    2251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 2,
        "incident_energy_lower_mev": 5.00e-1,
        "incident_energy_upper_mev": 1.353,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 2; file contains one scalar value.",
    },
    3251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 3,
        "incident_energy_lower_mev": 1.353,
        "incident_energy_upper_mev": 5.3526,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 3; file contains one scalar value.",
    },
    4251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 4,
        "incident_energy_lower_mev": 5.3526,
        "incident_energy_upper_mev": 6.07,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 4; file contains one scalar value.",
    },
    5251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 5,
        "incident_energy_lower_mev": 6.07,
        "incident_energy_upper_mev": 10.0,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 5; file contains one scalar value.",
    },
    6251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 6,
        "incident_energy_lower_mev": 10.0,
        "incident_energy_upper_mev": 13.0,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 6; file contains one scalar value.",
    },
    7251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 7,
        "incident_energy_lower_mev": 13.0,
        "incident_energy_upper_mev": 14.0,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 7; file contains one scalar value.",
    },
    8251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 8,
        "incident_energy_lower_mev": 14.0,
        "incident_energy_upper_mev": 15.0,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 8; file contains one scalar value.",
    },
    9251: {
        "quantity": "mubar",
        "base_mt": 251,
        "incident_group": 9,
        "incident_energy_lower_mev": 15.0,
        "incident_energy_upper_mev": 20.0,
        "description": "Average cosine of the elastic-scattering angle for incident-energy group 9; file contains one scalar value.",
    },
}


__all__ = [
    "PFNS_PSEUDO_IDS",
    "MUBAR_PSEUDO_IDS",
]
