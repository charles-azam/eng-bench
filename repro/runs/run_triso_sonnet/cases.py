"""Case data transcribed from inputs/01_particles_and_elements.md and inputs/02_cases.md."""

# Particle batches (inputs 01)
BATCH_EUO2308 = dict(
    d_kernel=497e-6, t_buffer=94e-6, t_ipyc=41e-6, t_sic=36e-6, t_opyc=40e-6,
    rho_kernel=10.81e3, rho_buffer=1.00e3, rho_ipyc=1.9e3, rho_sic=3.20e3, rho_opyc=1.88e3,
    enrichment=0.0982,
)
BATCH_EUO2358 = dict(
    d_kernel=508e-6, t_buffer=102e-6, t_ipyc=39e-6, t_sic=36e-6, t_opyc=38e-6,
    rho_kernel=10.72e3, rho_buffer=1.02e3, rho_ipyc=1.92e3, rho_sic=3.20e3, rho_opyc=1.92e3,
    enrichment=0.106,
)

# Furnace schedules: list of (setpoint_C, ramp_h, hold_h). ramp is time to REACH setpoint from
# the previous one; hold is time held AT the setpoint (may be 0/None).
SCHEDULE_A1 = [(300, None, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 16.5), (1550, 6.5, 0),
               (300, 1, 0), (1600, 9, 500)]
SCHEDULE_A2 = [(300, None, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 13.5), (1800, 12, 25.5),
               (300, 1, 0), (1050, 1.5, 19.5), (1250, 0.5, 19), (1800, 12, 74.5)]
SCHEDULE_B = [(300, None, 7), (1050, 2, 13.5), (1600, 11, 99), (20, 17, 0),
              (1700, 5.5, 100), (20, 17, 0), (1800, 2, 100), (20, 17, 0),
              (300, 7, 0), (1800, 1, 300)]
SCHEDULE_C = [(300, None, 0.5), (1050, 1.5, 5.5), (1250, 0.5, 13.5), (1600, 7.5, 304)]

CASES = {
    "A1": dict(
        element="HFR-K3/1 sphere", batch=BATCH_EUO2308, n_particles=16400,
        hm_g=10.22, burnup_fima=7.7, fluence_e01=3.9e25,
        t_irr_C=(1020, 1216),  # surface, centre
        schedule=SCHEDULE_A1, t_irr_h=8616, peak_T=1600, peak_hold_h=500,
    ),
    "A2": dict(
        element="HFR-K3/3 sphere", batch=BATCH_EUO2308, n_particles=16400,
        hm_g=10.22, burnup_fima=10.2, fluence_e01=6.0e25,
        t_irr_C=(700, 983),
        schedule=SCHEDULE_A2, t_irr_h=8616, peak_T=1800, peak_hold_h=100,
    ),
    "B": dict(
        element="HFR-K6/3 sphere", batch=BATCH_EUO2358, n_particles=14580,
        hm_g=9.4346, burnup_fima=10.9, fluence_e01=4.8e25,
        t_irr_C=(1140, 1140),
        schedule=SCHEDULE_B, t_irr_h=15216, peak_T=1800, peak_hold_h=400,
    ),
    "C1": dict(
        element="HFR-P4/3-7 compact", batch=BATCH_EUO2308, n_particles=1631,
        hm_g=1.018, burnup_fima=13.9, fluence_e01=7.5e25,
        t_irr_C=(1075, 1075),
        schedule=SCHEDULE_C, t_irr_h=8424, peak_T=1600, peak_hold_h=304,
    ),
    "C2": dict(
        element="HFR-P4/1-12 compact", batch=BATCH_EUO2308, n_particles=1631,
        hm_g=1.018, burnup_fima=11.1, fluence_e01=5.5e25,
        t_irr_C=(940, 940),
        schedule=SCHEDULE_C, t_irr_h=8424, peak_T=1600, peak_hold_h=304,
    ),
}
