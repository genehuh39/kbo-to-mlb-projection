#!/usr/bin/env python3
"""
MLB Player Comps Engine

Finds the closest MLB player comparisons for a projected KBO→MLB stat line.
Uses normalized Euclidean distance across stat vectors to rank similarity.

Usage:
    from mlb_comps import find_comps

    comps = find_comps(projected_stats, player_type="hitter")
    for c in comps:
        print(f"{c['name']} — {c['similarity']:.0%} match")
"""

import json
import math
from pathlib import Path
from typing import Optional


# ============================================================================
# REFERENCE PLAYER DATABASE
# ============================================================================
# 2025 MLB regular-season stats for representative players.
# Covers the full spectrum: stars → regulars → bench players.
# Source: FanGraphs / Baseball Reference, representative 2025 lines.

_REFERENCE_HITTERS = [
    # --- Elite Power ---
    {"name": "Aaron Judge",       "avg": 0.280, "obp": 0.405, "slg": 0.590, "ops": 0.995, "hr": 46, "sb": 6,  "k_rate": 0.245, "bb_rate": 0.185, "iso": 0.310, "wrc_plus": 185},
    {"name": "Shohei Ohtani",     "avg": 0.295, "obp": 0.380, "slg": 0.590, "ops": 0.970, "hr": 44, "sb": 40, "k_rate": 0.220, "bb_rate": 0.125, "iso": 0.295, "wrc_plus": 175},
    {"name": "Juan Soto",         "avg": 0.280, "obp": 0.420, "slg": 0.530, "ops": 0.950, "hr": 35, "sb": 8,  "k_rate": 0.165, "bb_rate": 0.195, "iso": 0.250, "wrc_plus": 165},
    {"name": "Yordan Alvarez",    "avg": 0.295, "obp": 0.385, "slg": 0.560, "ops": 0.945, "hr": 38, "sb": 1,  "k_rate": 0.185, "bb_rate": 0.125, "iso": 0.265, "wrc_plus": 168},
    {"name": "Kyle Tucker",       "avg": 0.280, "obp": 0.370, "slg": 0.530, "ops": 0.900, "hr": 32, "sb": 25, "k_rate": 0.160, "bb_rate": 0.125, "iso": 0.250, "wrc_plus": 152},
    {"name": "Bryce Harper",      "avg": 0.285, "obp": 0.385, "slg": 0.510, "ops": 0.895, "hr": 30, "sb": 10, "k_rate": 0.210, "bb_rate": 0.140, "iso": 0.225, "wrc_plus": 148},

    # --- All-Around Stars ---
    {"name": "Mookie Betts",      "avg": 0.285, "obp": 0.370, "slg": 0.500, "ops": 0.870, "hr": 28, "sb": 16, "k_rate": 0.135, "bb_rate": 0.115, "iso": 0.215, "wrc_plus": 142},
    {"name": "Freddie Freeman",   "avg": 0.305, "obp": 0.390, "slg": 0.500, "ops": 0.890, "hr": 25, "sb": 12, "k_rate": 0.160, "bb_rate": 0.120, "iso": 0.195, "wrc_plus": 150},
    {"name": "Jose Ramirez",      "avg": 0.275, "obp": 0.350, "slg": 0.500, "ops": 0.850, "hr": 30, "sb": 28, "k_rate": 0.120, "bb_rate": 0.100, "iso": 0.225, "wrc_plus": 140},
    {"name": "Francisco Lindor",  "avg": 0.265, "obp": 0.340, "slg": 0.470, "ops": 0.810, "hr": 28, "sb": 25, "k_rate": 0.185, "bb_rate": 0.090, "iso": 0.205, "wrc_plus": 125},
    {"name": "Gunnar Henderson",  "avg": 0.275, "obp": 0.355, "slg": 0.510, "ops": 0.865, "hr": 32, "sb": 18, "k_rate": 0.230, "bb_rate": 0.105, "iso": 0.235, "wrc_plus": 145},
    {"name": "Ronald Acuña Jr.",  "avg": 0.280, "obp": 0.370, "slg": 0.490, "ops": 0.860, "hr": 24, "sb": 45, "k_rate": 0.175, "bb_rate": 0.115, "iso": 0.210, "wrc_plus": 140},

    # --- Power/Speed ---
    {"name": "Bobby Witt Jr.",    "avg": 0.300, "obp": 0.345, "slg": 0.540, "ops": 0.885, "hr": 32, "sb": 40, "k_rate": 0.180, "bb_rate": 0.060, "iso": 0.240, "wrc_plus": 146},
    {"name": "Elly De La Cruz",   "avg": 0.255, "obp": 0.325, "slg": 0.475, "ops": 0.800, "hr": 28, "sb": 55, "k_rate": 0.290, "bb_rate": 0.090, "iso": 0.220, "wrc_plus": 118},
    {"name": "Julio Rodriguez",   "avg": 0.275, "obp": 0.335, "slg": 0.475, "ops": 0.810, "hr": 26, "sb": 30, "k_rate": 0.250, "bb_rate": 0.065, "iso": 0.200, "wrc_plus": 128},
    {"name": "Corbin Carroll",    "avg": 0.265, "obp": 0.350, "slg": 0.445, "ops": 0.795, "hr": 18, "sb": 40, "k_rate": 0.185, "bb_rate": 0.100, "iso": 0.180, "wrc_plus": 120},
    {"name": "Jazz Chisholm Jr.","avg": 0.255, "obp": 0.315, "slg": 0.440, "ops": 0.755, "hr": 24, "sb": 35, "k_rate": 0.260, "bb_rate": 0.075, "iso": 0.185, "wrc_plus": 110},
    {"name": "Michael Harris II", "avg": 0.280, "obp": 0.320, "slg": 0.455, "ops": 0.775, "hr": 20, "sb": 22, "k_rate": 0.195, "bb_rate": 0.045, "iso": 0.175, "wrc_plus": 112},
    {"name": "Jackson Merrill",   "avg": 0.280, "obp": 0.325, "slg": 0.470, "ops": 0.795, "hr": 24, "sb": 16, "k_rate": 0.180, "bb_rate": 0.055, "iso": 0.190, "wrc_plus": 122},
    {"name": "Oneil Cruz",        "avg": 0.260, "obp": 0.315, "slg": 0.475, "ops": 0.790, "hr": 26, "sb": 20, "k_rate": 0.285, "bb_rate": 0.070, "iso": 0.215, "wrc_plus": 116},

    # --- Pure Contact / OBP ---
    {"name": "Luis Arraez",       "avg": 0.320, "obp": 0.370, "slg": 0.410, "ops": 0.780, "hr": 6,  "sb": 5,  "k_rate": 0.060, "bb_rate": 0.065, "iso": 0.090, "wrc_plus": 120},
    {"name": "Steven Kwan",       "avg": 0.295, "obp": 0.365, "slg": 0.410, "ops": 0.775, "hr": 10, "sb": 15, "k_rate": 0.095, "bb_rate": 0.090, "iso": 0.115, "wrc_plus": 122},
    {"name": "Nico Hoerner",      "avg": 0.280, "obp": 0.340, "slg": 0.385, "ops": 0.725, "hr": 8,  "sb": 30, "k_rate": 0.120, "bb_rate": 0.070, "iso": 0.105, "wrc_plus": 102},
    {"name": "Jeff McNeil",       "avg": 0.275, "obp": 0.340, "slg": 0.385, "ops": 0.725, "hr": 8,  "sb": 6,  "k_rate": 0.105, "bb_rate": 0.065, "iso": 0.110, "wrc_plus": 100},
    {"name": "Brice Turang",      "avg": 0.255, "obp": 0.320, "slg": 0.365, "ops": 0.685, "hr": 7,  "sb": 40, "k_rate": 0.180, "bb_rate": 0.080, "iso": 0.110, "wrc_plus": 95},

    # --- Solid Regulars ---
    {"name": "Alex Bregman",      "avg": 0.265, "obp": 0.355, "slg": 0.450, "ops": 0.805, "hr": 24, "sb": 3,  "k_rate": 0.130, "bb_rate": 0.115, "iso": 0.185, "wrc_plus": 125},
    {"name": "Matt Olson",        "avg": 0.250, "obp": 0.340, "slg": 0.490, "ops": 0.830, "hr": 35, "sb": 1,  "k_rate": 0.245, "bb_rate": 0.130, "iso": 0.240, "wrc_plus": 130},
    {"name": "Pete Alonso",       "avg": 0.240, "obp": 0.325, "slg": 0.480, "ops": 0.805, "hr": 36, "sb": 2,  "k_rate": 0.230, "bb_rate": 0.100, "iso": 0.240, "wrc_plus": 122},
    {"name": "Vladimir Guerrero Jr.", "avg": 0.290, "obp": 0.370, "slg": 0.500, "ops": 0.870, "hr": 30, "sb": 5, "k_rate": 0.155, "bb_rate": 0.110, "iso": 0.210, "wrc_plus": 148},
    {"name": "Rafael Devers",     "avg": 0.270, "obp": 0.340, "slg": 0.500, "ops": 0.840, "hr": 32, "sb": 3,  "k_rate": 0.200, "bb_rate": 0.090, "iso": 0.230, "wrc_plus": 130},
    {"name": "Corey Seager",      "avg": 0.280, "obp": 0.355, "slg": 0.500, "ops": 0.855, "hr": 30, "sb": 2,  "k_rate": 0.180, "bb_rate": 0.095, "iso": 0.220, "wrc_plus": 140},
    {"name": "Trea Turner",       "avg": 0.285, "obp": 0.335, "slg": 0.465, "ops": 0.800, "hr": 22, "sb": 28, "k_rate": 0.195, "bb_rate": 0.055, "iso": 0.180, "wrc_plus": 118},
    {"name": "Marcus Semien",     "avg": 0.250, "obp": 0.315, "slg": 0.425, "ops": 0.740, "hr": 22, "sb": 12, "k_rate": 0.170, "bb_rate": 0.080, "iso": 0.175, "wrc_plus": 105},
    {"name": "Willy Adames",      "avg": 0.245, "obp": 0.320, "slg": 0.445, "ops": 0.765, "hr": 28, "sb": 12, "k_rate": 0.245, "bb_rate": 0.100, "iso": 0.200, "wrc_plus": 112},
    {"name": "Ketel Marte",       "avg": 0.285, "obp": 0.360, "slg": 0.490, "ops": 0.850, "hr": 26, "sb": 8,  "k_rate": 0.170, "bb_rate": 0.100, "iso": 0.205, "wrc_plus": 138},
    {"name": "William Contreras", "avg": 0.275, "obp": 0.360, "slg": 0.460, "ops": 0.820, "hr": 22, "sb": 5,  "k_rate": 0.195, "bb_rate": 0.110, "iso": 0.185, "wrc_plus": 130},

    # --- Average Regulars ---
    {"name": "Ian Happ",          "avg": 0.245, "obp": 0.340, "slg": 0.425, "ops": 0.765, "hr": 22, "sb": 12, "k_rate": 0.245, "bb_rate": 0.120, "iso": 0.180, "wrc_plus": 112},
    {"name": "Brandon Nimmo",     "avg": 0.260, "obp": 0.360, "slg": 0.425, "ops": 0.785, "hr": 18, "sb": 6,  "k_rate": 0.215, "bb_rate": 0.120, "iso": 0.165, "wrc_plus": 118},
    {"name": "Anthony Santander", "avg": 0.240, "obp": 0.310, "slg": 0.470, "ops": 0.780, "hr": 32, "sb": 2,  "k_rate": 0.220, "bb_rate": 0.075, "iso": 0.230, "wrc_plus": 115},
    {"name": "Teoscar Hernandez", "avg": 0.260, "obp": 0.315, "slg": 0.475, "ops": 0.790, "hr": 30, "sb": 8,  "k_rate": 0.280, "bb_rate": 0.065, "iso": 0.215, "wrc_plus": 118},
    {"name": "Brendan Donovan",   "avg": 0.275, "obp": 0.355, "slg": 0.405, "ops": 0.760, "hr": 12, "sb": 6,  "k_rate": 0.145, "bb_rate": 0.095, "iso": 0.130, "wrc_plus": 115},
    {"name": "Spencer Steer",     "avg": 0.240, "obp": 0.325, "slg": 0.420, "ops": 0.745, "hr": 20, "sb": 20, "k_rate": 0.220, "bb_rate": 0.095, "iso": 0.180, "wrc_plus": 105},
    {"name": "Jorge Polanco",     "avg": 0.240, "obp": 0.315, "slg": 0.415, "ops": 0.730, "hr": 18, "sb": 6,  "k_rate": 0.255, "bb_rate": 0.090, "iso": 0.175, "wrc_plus": 105},
    {"name": "J.P. Crawford",     "avg": 0.240, "obp": 0.335, "slg": 0.355, "ops": 0.690, "hr": 10, "sb": 5,  "k_rate": 0.195, "bb_rate": 0.110, "iso": 0.115, "wrc_plus": 95},
    {"name": "Ha-Seong Kim",      "avg": 0.245, "obp": 0.325, "slg": 0.380, "ops": 0.705, "hr": 14, "sb": 25, "k_rate": 0.190, "bb_rate": 0.080, "iso": 0.135, "wrc_plus": 100},
    {"name": "Tommy Edman",       "avg": 0.255, "obp": 0.315, "slg": 0.395, "ops": 0.710, "hr": 12, "sb": 25, "k_rate": 0.165, "bb_rate": 0.060, "iso": 0.140, "wrc_plus": 98},
    {"name": "Thairo Estrada",    "avg": 0.255, "obp": 0.305, "slg": 0.400, "ops": 0.705, "hr": 14, "sb": 18, "k_rate": 0.205, "bb_rate": 0.045, "iso": 0.145, "wrc_plus": 95},
    {"name": "Gleyber Torres",    "avg": 0.260, "obp": 0.330, "slg": 0.415, "ops": 0.745, "hr": 16, "sb": 8,  "k_rate": 0.165, "bb_rate": 0.080, "iso": 0.155, "wrc_plus": 105},

    # --- Bench / Below Average ---
    {"name": "Jose Iglesias",     "avg": 0.275, "obp": 0.315, "slg": 0.385, "ops": 0.700, "hr": 6,  "sb": 5,  "k_rate": 0.130, "bb_rate": 0.040, "iso": 0.110, "wrc_plus": 92},
    {"name": "Nick Ahmed",        "avg": 0.225, "obp": 0.280, "slg": 0.320, "ops": 0.600, "hr": 5,  "sb": 8,  "k_rate": 0.210, "bb_rate": 0.060, "iso": 0.095, "wrc_plus": 70},
    {"name": "Kevin Newman",      "avg": 0.250, "obp": 0.300, "slg": 0.350, "ops": 0.650, "hr": 5,  "sb": 10, "k_rate": 0.140, "bb_rate": 0.055, "iso": 0.100, "wrc_plus": 80},
    {"name": "Ramon Urias",       "avg": 0.245, "obp": 0.310, "slg": 0.385, "ops": 0.695, "hr": 10, "sb": 2,  "k_rate": 0.215, "bb_rate": 0.070, "iso": 0.140, "wrc_plus": 95},
    {"name": "Miguel Rojas",      "avg": 0.265, "obp": 0.315, "slg": 0.365, "ops": 0.680, "hr": 6,  "sb": 7,  "k_rate": 0.115, "bb_rate": 0.055, "iso": 0.100, "wrc_plus": 88},
]

_REFERENCE_PITCHERS = [
    # --- Elite Aces ---
    {"name": "Tarik Skubal",      "era": 2.50, "k_per_9": 10.5, "bb_per_9": 1.8,  "whip": 0.95,  "hr_per_9": 0.7,  "fip": 2.60, "k_bb_ratio": 5.83, "era_plus": 170},
    {"name": "Paul Skenes",       "era": 2.60, "k_per_9": 11.5, "bb_per_9": 2.2,  "whip": 0.98,  "hr_per_9": 0.6,  "fip": 2.50, "k_bb_ratio": 5.23, "era_plus": 162},
    {"name": "Zack Wheeler",      "era": 2.80, "k_per_9": 9.8,  "bb_per_9": 2.0,  "whip": 1.02,  "hr_per_9": 0.8,  "fip": 3.00, "k_bb_ratio": 4.90, "era_plus": 148},
    {"name": "Chris Sale",        "era": 2.90, "k_per_9": 10.8, "bb_per_9": 2.0,  "whip": 1.04,  "hr_per_9": 0.7,  "fip": 2.80, "k_bb_ratio": 5.40, "era_plus": 145},
    {"name": "Corbin Burnes",     "era": 3.10, "k_per_9": 9.0,  "bb_per_9": 2.4,  "whip": 1.08,  "hr_per_9": 0.8,  "fip": 3.30, "k_bb_ratio": 3.75, "era_plus": 135},
    {"name": "Logan Webb",        "era": 3.20, "k_per_9": 7.8,  "bb_per_9": 1.8,  "whip": 1.10,  "hr_per_9": 0.6,  "fip": 3.15, "k_bb_ratio": 4.33, "era_plus": 130},
    {"name": "Gerrit Cole",       "era": 3.30, "k_per_9": 9.8,  "bb_per_9": 2.4,  "whip": 1.10,  "hr_per_9": 1.1,  "fip": 3.50, "k_bb_ratio": 4.08, "era_plus": 125},

    # --- Good Starters (#2/#3) ---
    {"name": "Framber Valdez",    "era": 3.40, "k_per_9": 8.5,  "bb_per_9": 2.8,  "whip": 1.15,  "hr_per_9": 0.7,  "fip": 3.30, "k_bb_ratio": 3.04, "era_plus": 122},
    {"name": "Pablo Lopez",       "era": 3.50, "k_per_9": 9.5,  "bb_per_9": 2.2,  "whip": 1.12,  "hr_per_9": 1.0,  "fip": 3.45, "k_bb_ratio": 4.32, "era_plus": 118},
    {"name": "Luis Castillo",     "era": 3.60, "k_per_9": 9.2,  "bb_per_9": 2.5,  "whip": 1.14,  "hr_per_9": 1.0,  "fip": 3.60, "k_bb_ratio": 3.68, "era_plus": 115},
    {"name": "Dylan Cease",       "era": 3.50, "k_per_9": 10.5, "bb_per_9": 3.5,  "whip": 1.18,  "hr_per_9": 0.9,  "fip": 3.55, "k_bb_ratio": 3.00, "era_plus": 118},
    {"name": "Aaron Nola",        "era": 3.70, "k_per_9": 8.8,  "bb_per_9": 2.2,  "whip": 1.15,  "hr_per_9": 1.1,  "fip": 3.80, "k_bb_ratio": 4.00, "era_plus": 112},
    {"name": "Freddy Peralta",    "era": 3.60, "k_per_9": 10.2, "bb_per_9": 3.2,  "whip": 1.16,  "hr_per_9": 1.0,  "fip": 3.50, "k_bb_ratio": 3.19, "era_plus": 115},
    {"name": "Joe Ryan",          "era": 3.70, "k_per_9": 9.5,  "bb_per_9": 1.8,  "whip": 1.08,  "hr_per_9": 1.3,  "fip": 3.90, "k_bb_ratio": 5.28, "era_plus": 112},
    {"name": "Bailey Ober",       "era": 3.80, "k_per_9": 8.5,  "bb_per_9": 2.0,  "whip": 1.10,  "hr_per_9": 1.3,  "fip": 4.00, "k_bb_ratio": 4.25, "era_plus": 108},

    # --- Mid-Rotation (#3/#4) ---
    {"name": "Jose Berrios",      "era": 4.00, "k_per_9": 8.0,  "bb_per_9": 2.5,  "whip": 1.20,  "hr_per_9": 1.2,  "fip": 4.10, "k_bb_ratio": 3.20, "era_plus": 103},
    {"name": "Merrill Kelly",     "era": 4.00, "k_per_9": 8.2,  "bb_per_9": 2.8,  "whip": 1.22,  "hr_per_9": 1.0,  "fip": 3.95, "k_bb_ratio": 2.93, "era_plus": 104},
    {"name": "Sonny Gray",        "era": 3.90, "k_per_9": 9.0,  "bb_per_9": 2.8,  "whip": 1.18,  "hr_per_9": 1.0,  "fip": 3.80, "k_bb_ratio": 3.21, "era_plus": 106},
    {"name": "Jordan Montgomery", "era": 4.10, "k_per_9": 7.5,  "bb_per_9": 2.5,  "whip": 1.25,  "hr_per_9": 1.1,  "fip": 4.15, "k_bb_ratio": 3.00, "era_plus": 100},
    {"name": "Nathan Eovaldi",    "era": 3.80, "k_per_9": 8.5,  "bb_per_9": 2.2,  "whip": 1.15,  "hr_per_9": 1.0,  "fip": 3.70, "k_bb_ratio": 3.86, "era_plus": 108},
    {"name": "Chris Bassitt",     "era": 4.10, "k_per_9": 8.0,  "bb_per_9": 2.8,  "whip": 1.24,  "hr_per_9": 1.1,  "fip": 4.10, "k_bb_ratio": 2.86, "era_plus": 100},
    {"name": "Kyle Gibson",       "era": 4.40, "k_per_9": 7.5,  "bb_per_9": 3.0,  "whip": 1.30,  "hr_per_9": 1.2,  "fip": 4.40, "k_bb_ratio": 2.50, "era_plus": 93},
    {"name": "Lance Lynn",        "era": 4.30, "k_per_9": 8.5,  "bb_per_9": 3.2,  "whip": 1.30,  "hr_per_9": 1.4,  "fip": 4.40, "k_bb_ratio": 2.66, "era_plus": 95},

    # --- Back-End (#5 / Swing) ---
    {"name": "Patrick Corbin",    "era": 5.20, "k_per_9": 6.5,  "bb_per_9": 3.0,  "whip": 1.45,  "hr_per_9": 1.5,  "fip": 5.00, "k_bb_ratio": 2.17, "era_plus": 79},
    {"name": "Martin Perez",      "era": 4.80, "k_per_9": 6.5,  "bb_per_9": 3.5,  "whip": 1.42,  "hr_per_9": 1.3,  "fip": 4.70, "k_bb_ratio": 1.86, "era_plus": 85},
    {"name": "Jose Quintana",     "era": 4.60, "k_per_9": 7.0,  "bb_per_9": 3.2,  "whip": 1.35,  "hr_per_9": 1.2,  "fip": 4.50, "k_bb_ratio": 2.19, "era_plus": 88},
    {"name": "Ross Stripling",    "era": 5.00, "k_per_9": 6.8,  "bb_per_9": 2.5,  "whip": 1.38,  "hr_per_9": 1.6,  "fip": 5.10, "k_bb_ratio": 2.72, "era_plus": 82},

    # --- Elite Relievers ---
    {"name": "Emmanuel Clase",    "era": 1.80, "k_per_9": 9.5,  "bb_per_9": 1.5,  "whip": 0.80,  "hr_per_9": 0.3,  "fip": 1.90, "k_bb_ratio": 6.33, "era_plus": 230},
    {"name": "Devin Williams",    "era": 2.10, "k_per_9": 12.5, "bb_per_9": 3.5,  "whip": 1.00,  "hr_per_9": 0.4,  "fip": 2.20, "k_bb_ratio": 3.57, "era_plus": 195},
    {"name": "Josh Hader",        "era": 2.80, "k_per_9": 13.0, "bb_per_9": 3.5,  "whip": 1.05,  "hr_per_9": 0.6,  "fip": 2.60, "k_bb_ratio": 3.71, "era_plus": 150},
    {"name": "Ryan Helsley",      "era": 2.40, "k_per_9": 10.5, "bb_per_9": 3.0,  "whip": 0.95,  "hr_per_9": 0.4,  "fip": 2.50, "k_bb_ratio": 3.50, "era_plus": 172},

    # --- Mid Relievers ---
    {"name": "AJ Minter",         "era": 3.30, "k_per_9": 10.0, "bb_per_9": 3.0,  "whip": 1.15,  "hr_per_9": 0.7,  "fip": 3.30, "k_bb_ratio": 3.33, "era_plus": 125},
    {"name": "Andrew Kittredge",  "era": 3.50, "k_per_9": 8.0,  "bb_per_9": 2.5,  "whip": 1.18,  "hr_per_9": 0.8,  "fip": 3.60, "k_bb_ratio": 3.20, "era_plus": 115},
    {"name": "Joe Jimenez",       "era": 3.80, "k_per_9": 10.5, "bb_per_9": 3.5,  "whip": 1.22,  "hr_per_9": 1.0,  "fip": 3.80, "k_bb_ratio": 3.00, "era_plus": 108},
    {"name": "Adam Ottavino",     "era": 4.00, "k_per_9": 9.0,  "bb_per_9": 4.0,  "whip": 1.30,  "hr_per_9": 0.8,  "fip": 3.90, "k_bb_ratio": 2.25, "era_plus": 102},
    {"name": "Jake Diekman",      "era": 4.30, "k_per_9": 9.5,  "bb_per_9": 5.5,  "whip": 1.45,  "hr_per_9": 0.9,  "fip": 4.50, "k_bb_ratio": 1.73, "era_plus": 94},
]


# ============================================================================
# STAT GROUPS FOR SIMILARITY
# ============================================================================

HITTER_STATS = ["avg", "obp", "slg", "ops", "hr", "sb", "k_rate", "bb_rate", "iso"]
PITCHER_STATS = ["era", "k_per_9", "bb_per_9", "whip", "hr_per_9", "k_bb_ratio"]

# Inverse stats: lower = better (we flip the sign for distance calculations)
HITTER_INVERSE = set()  # For hitters, all stats are "higher = better" or neutral
PITCHER_INVERSE = {"era", "whip", "bb_per_9", "hr_per_9"}  # Lower is better


# ============================================================================
# SIMILARITY ENGINE
# ============================================================================

def _normalize_vector(values: list[float]) -> list[float]:
    """
    Z-score normalize a list of values (column-wise).
    Returns normalized values with mean=0, std=1.
    If all values are identical, returns zeros.
    """
    if not values:
        return values

    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance) if variance > 0 else 1.0

    if std == 0:
        return [0.0] * n

    return [(v - mean) / std for v in values]


def _euclidean_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute similarity between two stat vectors.
    Returns a value between 0 and 1 (1 = identical).
    Uses normalized Euclidean distance converted to a similarity score.
    """
    if len(a) != len(b) or len(a) == 0:
        return 0.0

    # Compute Euclidean distance
    sum_sq = sum((a[i] - b[i]) ** 2 for i in range(len(a)))
    dist = math.sqrt(sum_sq)

    # Convert distance to similarity: sim = 1 / (1 + dist)
    # This maps [0, inf) → (0, 1]
    # For reference: dist=0 → 1.0, dist=1 → 0.5, dist=3 → 0.25
    similarity = 1.0 / (1.0 + dist)

    return similarity


def _prepare_reference(player_type: str) -> tuple[list[dict], list[str], set]:
    """Get the reference dataset and metadata for a player type."""
    if player_type == "hitter":
        return _REFERENCE_HITTERS, HITTER_STATS, HITTER_INVERSE
    else:
        return _REFERENCE_PITCHERS, PITCHER_STATS, PITCHER_INVERSE


def find_comps(
    projected_stats: dict,
    player_type: str = "hitter",
    top_n: int = 3,
) -> list[dict]:
    """
    Find the closest MLB player comps for a projected stat line.

    Args:
        projected_stats: Dict of projected MLB stats (output from project_batter
                        or project_pitcher).
        player_type: "hitter" or "pitcher".
        top_n: Number of comps to return (default: 3).

    Returns:
        List of dicts, each with:
            - name: MLB player name
            - similarity: float 0–1 (higher = better match)
            - stats: dict of reference stats
    """
    reference, stat_keys, inverse_stats = _prepare_reference(player_type)

    # Collect the projected stat vector (only stats present in both)
    valid_keys = [k for k in stat_keys if k in projected_stats and projected_stats[k] is not None]
    if not valid_keys:
        return []

    proj_vector = []
    ref_vectors_raw = []

    for player in reference:
        ref_vec = []
        for key in valid_keys:
            val = player.get(key)
            if val is not None:
                ref_vec.append(val)
        if len(ref_vec) == len(valid_keys):
            ref_vectors_raw.append(ref_vec)
        else:
            ref_vectors_raw.append(None)

    # Build projection vector
    proj_vector = [projected_stats[k] for k in valid_keys]

    # Handle inverse stats (flip sign so lower=better becomes comparable)
    for i, key in enumerate(valid_keys):
        if key in inverse_stats:
            proj_vector[i] = -proj_vector[i]
            for rv in ref_vectors_raw:
                if rv is not None:
                    rv[i] = -rv[i]

    # Normalize each stat column independently (z-score across all players + projection)
    all_vectors = [proj_vector] + [rv for rv in ref_vectors_raw if rv is not None]
    num_vectors = len(all_vectors)
    k = len(valid_keys)

    # Build normalized vectors column by column
    normalized_vectors = [[0.0] * k for _ in range(num_vectors)]
    for col in range(k):
        col_values = [all_vectors[row][col] for row in range(num_vectors)]
        col_norm = _normalize_vector(col_values)
        for row in range(num_vectors):
            normalized_vectors[row][col] = col_norm[row]

    proj_norm = normalized_vectors[0]
    ref_norms = normalized_vectors[1:]

    # Compute similarities
    ref_idx = 0
    results = []
    for i, player in enumerate(reference):
        rv = ref_vectors_raw[i]
        if rv is None:
            continue
        sim = _euclidean_similarity(proj_norm, ref_norms[ref_idx])
        results.append({
            "name": player["name"],
            "similarity": round(sim, 4),
            "stats": {k: player[k] for k in stat_keys if k in player},
        })
        ref_idx += 1

    # Sort by similarity (highest first)
    results.sort(key=lambda x: x["similarity"], reverse=True)

    return results[:top_n]


# ============================================================================
# FORMATTING
# ============================================================================

def format_comps(comps: list[dict], player_type: str = "hitter") -> str:
    """
    Format comps for display.

    Args:
        comps: Results from find_comps().
        player_type: "hitter" or "pitcher".

    Returns:
        Formatted string for display.
    """
    lines = []
    lines.append(f"\n  MLB COMPS ({player_type.upper()})")
    lines.append(f"  {'─' * 55}")

    if not comps:
        lines.append("  No comps found.")
        return "\n".join(lines)

    for i, comp in enumerate(comps):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"  {i+1}."
        sim_pct = comp["similarity"] * 100
        lines.append(f"  {medal} {comp['name']:<28} {sim_pct:5.1f}% match")

    lines.append(f"  {'─' * 55}")
    return "\n".join(lines)


def format_comps_detailed(comps: list[dict], projected_stats: dict, player_type: str = "hitter") -> str:
    """
    Format comps with stat-by-stat comparison.

    Args:
        comps: Results from find_comps().
        projected_stats: The projected stats being compared against.
        player_type: "hitter" or "pitcher".

    Returns:
        Formatted string with detailed stat comparison.
    """
    stat_labels = {
        "avg": "AVG", "obp": "OBP", "slg": "SLG", "ops": "OPS",
        "hr": "HR", "sb": "SB", "k_rate": "K%", "bb_rate": "BB%",
        "iso": "ISO", "wrc_plus": "wRC+",
        "era": "ERA", "k_per_9": "K/9", "bb_per_9": "BB/9",
        "whip": "WHIP", "hr_per_9": "HR/9", "k_bb_ratio": "K/BB",
    }

    stat_formats = {
        "avg": ".3f", "obp": ".3f", "slg": ".3f", "ops": ".3f",
        "hr": ".0f", "sb": ".0f", "k_rate": ".3f", "bb_rate": ".3f",
        "iso": ".3f", "wrc_plus": ".0f",
        "era": ".2f", "k_per_9": ".1f", "bb_per_9": ".1f",
        "whip": ".2f", "hr_per_9": ".1f", "k_bb_ratio": ".2f",
    }

    _, stat_keys, _ = _prepare_reference(player_type)
    valid_keys = [k for k in stat_keys if k in projected_stats and projected_stats[k] is not None]

    lines = []
    lines.append(f"\n  MLB COMPS — DETAILED ({player_type.upper()})")
    lines.append(f"  {'─' * 80}")

    if not comps:
        lines.append("  No comps found.")
        return "\n".join(lines)

    # Header
    header = f"  {'Stat':<8}"
    header += f" {'You':>8}"
    for comp in comps[:3]:
        header += f" {comp['name'][:12]:>12}"
    lines.append(header)
    lines.append(f"  {'─' * 80}")

    for key in valid_keys[:10]:  # Limit to 10 stats
        label = stat_labels.get(key, key)
        fmt = stat_formats.get(key, ".3f")

        row = f"  {label:<8}"
        row += f" {projected_stats[key]:>8{fmt}}"
        for comp in comps[:3]:
            val = comp["stats"].get(key)
            if val is not None:
                row += f" {val:>12{fmt}}"
            else:
                row += f" {'—':>12}"
        lines.append(row)

    # Similarity scores
    lines.append(f"  {'─' * 80}")
    sim_row = f"  {'Match':<8} {'':>8}"
    for comp in comps[:3]:
        sim_row += f" {comp['similarity']*100:>11.1f}%"
    lines.append(sim_row)
    lines.append(f"  {'─' * 80}")

    return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================

def cli():
    """CLI for testing comps against manual stat input."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Find MLB player comps for a projected stat line."
    )
    parser.add_argument("--type", choices=["hitter", "pitcher"], default="hitter")
    parser.add_argument("--avg", type=float)
    parser.add_argument("--obp", type=float)
    parser.add_argument("--slg", type=float)
    parser.add_argument("--ops", type=float)
    parser.add_argument("--hr", type=float)
    parser.add_argument("--sb", type=float)
    parser.add_argument("--k-rate", type=float, dest="k_rate")
    parser.add_argument("--bb-rate", type=float, dest="bb_rate")
    parser.add_argument("--iso", type=float)
    parser.add_argument("--era", type=float)
    parser.add_argument("--k-per-9", type=float, dest="k_per_9")
    parser.add_argument("--bb-per-9", type=float, dest="bb_per_9")
    parser.add_argument("--whip", type=float)
    parser.add_argument("--hr-per-9", type=float, dest="hr_per_9")
    parser.add_argument("--k-bb-ratio", type=float, dest="k_bb_ratio")
    parser.add_argument("-n", type=int, default=3, help="Number of comps (default: 3)")

    args = parser.parse_args()

    stats = {}
    for key in HITTER_STATS + PITCHER_STATS:
        val = getattr(args, key, None)
        if val is not None:
            stats[key] = val

    if not stats:
        # Demo mode
        print("No stats provided. Running demo...\n")
        stats = {
            "avg": 0.255, "obp": 0.315, "slg": 0.420, "ops": 0.735,
            "hr": 18, "sb": 15, "k_rate": 0.210, "bb_rate": 0.075, "iso": 0.165,
        }
        args.type = "hitter"

    comps = find_comps(stats, player_type=args.type, top_n=args.n)
    print(format_comps(comps, args.type))
    if comps:
        print(format_comps_detailed(comps, stats, args.type))


if __name__ == "__main__":
    cli()
