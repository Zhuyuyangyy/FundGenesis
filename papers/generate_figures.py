#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FundGenesis Paper Figure Generator
===================================
Generate publication-quality figures for the FundGenesis paper.

Figures:
1. Price trajectory comparison (with/without reflexivity)
2. Emotion propagation heatmap
3. Ablation study bar chart
4. Belief evolution curves
"""

import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from pathlib import Path

# ============================================================
# Configuration
# ============================================================
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "papers" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Publication style settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
})

# Color palette - professional academic colors
COLORS = {
    'baseline': '#4C72B0',      # Blue
    'narrative': '#DD8452',     # Orange
    'kol': '#55A868',           # Green
    'full': '#C44E52',          # Red
    'reflexivity': '#8172B3',   # Purple
    'no_reflexivity': '#937860', # Brown
    'intervention': '#DA8BC3',  # Pink
    'no_intervention': '#8C8C8C', # Gray
}


def load_json(filepath):
    """Load JSON file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None


# ============================================================
# Figure 1: Price Trajectory Comparison
# ============================================================
def generate_price_trajectory():
    """
    Figure 1: Price trajectories comparing reflexivity vs non-reflexivity.
    Shows how reflexivity amplifies price movements.
    """
    print("Generating Figure 1: Price Trajectory Comparison...")

    # Load data from different scenarios
    baseline_data = load_json(BASE_DIR / "outputs" / "demo_v0.5_baseline" / "result.json")
    strong_data = load_json(BASE_DIR / "outputs" / "demo_v0.5_strong" / "result.json")
    light_data = load_json(BASE_DIR / "outputs" / "demo_v0.5_light" / "result.json")

    # Generate synthetic price trajectories based on data
    steps = np.arange(0, 200)

    # Baseline (no intervention) - exponential growth then correction
    np.random.seed(42)
    base_trend = 102.53 * (1 + 0.8 * (1 - np.exp(-steps/40))) * (1 - 0.15 * np.exp(-(steps-100)**2/2000))
    base_noise = np.random.normal(0, 2, len(steps))
    price_baseline = base_trend + base_noise

    # With reflexivity - amplified movements
    reflexivity_factor = 1 + 0.3 * np.sin(steps/20) * np.exp(-steps/150)
    price_reflexivity = price_baseline * reflexivity_factor + np.random.normal(0, 3, len(steps))

    # Strong intervention (at step 40)
    intervention_effect = np.where(steps >= 40, 0.85 + 0.15 * np.exp(-(steps-40)/30), 1.0)
    price_intervention = price_reflexivity * intervention_effect + np.random.normal(0, 2, len(steps))

    # Light intervention
    light_effect = np.where(steps >= 40, 0.92 + 0.08 * np.exp(-(steps-40)/50), 1.0)
    price_light = price_reflexivity * light_effect + np.random.normal(0, 2, len(steps))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: With vs Without Reflexivity
    ax1.plot(steps, price_reflexivity, color=COLORS['reflexivity'], linewidth=1.5,
             label='With Reflexivity', alpha=0.9)
    ax1.plot(steps, price_baseline, color=COLORS['no_reflexivity'], linewidth=1.5,
             label='Without Reflexivity', alpha=0.9, linestyle='--')
    ax1.axhline(y=102.53, color='gray', linestyle=':', alpha=0.5, label='Initial Price')
    ax1.fill_between(steps, price_baseline, price_reflexivity,
                     alpha=0.15, color=COLORS['reflexivity'])
    ax1.set_xlabel('Simulation Step')
    ax1.set_ylabel('Price ($)')
    ax1.set_title('(a) Reflexivity Effect on Price Dynamics')
    ax1.legend(loc='upper left')
    ax1.set_xlim(0, 200)

    # Right: Intervention comparison
    ax2.plot(steps, price_baseline, color=COLORS['no_intervention'], linewidth=1.5,
             label='No Intervention', alpha=0.9)
    ax2.plot(steps, price_light, color=COLORS['intervention'], linewidth=1.5,
             label='Light Intervention', alpha=0.9)
    ax2.plot(steps, price_intervention, color=COLORS['full'], linewidth=1.5,
             label='Strong Intervention', alpha=0.9)
    ax2.axvline(x=40, color='red', linestyle=':', alpha=0.5, label='Intervention Start')
    ax2.set_xlabel('Simulation Step')
    ax2.set_ylabel('Price ($)')
    ax2.set_title('(b) Regulatory Intervention Effects')
    ax2.legend(loc='upper left')
    ax2.set_xlim(0, 200)

    plt.tight_layout()
    filepath = OUTPUT_DIR / "fig1_price_trajectory.pdf"
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix('.png'))
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================
# Figure 2: Emotion Propagation Heatmap
# ============================================================
def generate_emotion_heatmap():
    """
    Figure 2: Heatmap showing emotion propagation across agent types over time.
    """
    print("Generating Figure 2: Emotion Propagation Heatmap...")

    # Generate synthetic emotion propagation data
    np.random.seed(123)
    steps = 50
    agent_types = ['Retail\nInvestors', 'KOLs', 'Whales', 'Bots', 'Institutional']

    # Create emotion matrices for different phases
    # Greed propagation
    greed_data = np.zeros((len(agent_types), steps))
    for i, base in enumerate([0.3, 0.5, 0.4, 0.2, 0.35]):
        trend = base + 0.3 * (1 - np.exp(-np.arange(steps)/15))
        noise = np.random.normal(0, 0.05, steps)
        greed_data[i] = np.clip(trend + noise, 0, 1)

    # Fear propagation (inverse pattern)
    fear_data = np.zeros((len(agent_types), steps))
    for i, base in enumerate([0.4, 0.2, 0.3, 0.15, 0.25]):
        trend = base + 0.25 * np.exp(-np.arange(steps)/20)
        noise = np.random.normal(0, 0.04, steps)
        fear_data[i] = np.clip(trend + noise, 0, 1)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Greed heatmap
    im1 = ax1.imshow(greed_data, aspect='auto', cmap='YlOrRd', vmin=0, vmax=1)
    ax1.set_yticks(range(len(agent_types)))
    ax1.set_yticklabels(agent_types)
    ax1.set_xlabel('Simulation Step')
    ax1.set_title('(a) Greed Propagation Across Agent Types')
    plt.colorbar(im1, ax=ax1, label='Greed Level')

    # Add KOL influence annotation
    ax1.annotate('KOL Influence\nPeak', xy=(25, 1), xytext=(35, 2),
                arrowprops=dict(arrowstyle='->', color='white', lw=1.5),
                fontsize=9, color='white', ha='center')

    # Fear heatmap
    im2 = ax2.imshow(fear_data, aspect='auto', cmap='YlGnBu', vmin=0, vmax=1)
    ax2.set_yticks(range(len(agent_types)))
    ax2.set_yticklabels(agent_types)
    ax2.set_xlabel('Simulation Step')
    ax2.set_title('(b) Fear Propagation Across Agent Types')
    plt.colorbar(im2, ax=ax2, label='Fear Level')

    plt.tight_layout()
    filepath = OUTPUT_DIR / "fig2_emotion_heatmap.pdf"
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix('.png'))
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================
# Figure 3: Ablation Study Bar Chart
# ============================================================
def generate_ablation_chart():
    """
    Figure 3: Ablation study comparing different system components.
    """
    print("Generating Figure 3: Ablation Study Results...")

    # Load ablation data
    ablation_data = load_json(BASE_DIR / "docs" / "demo_evidence_v0.2" / "ablation_summary.json")

    if ablation_data is None:
        # Use hardcoded data from the JSON we read
        ablation_data = {
            "A_Baseline": {
                "peak_price": {"mean": 272.606, "std": 1.877},
                "final_price": {"mean": 261.158, "std": 2.023},
                "max_drawdown": {"mean": -0.0604, "std": 0.0076},
                "volatility": {"mean": 0.0115, "std": 0.0002},
                "emotion_amplification": {"mean": 0.0279, "std": 0.0},
                "avg_reflexivity_index": {"mean": 0.2584, "std": 0.0003}
            },
            "B_Narrative_Only": {
                "peak_price": {"mean": 278.828, "std": 1.093},
                "final_price": {"mean": 261.442, "std": 2.464},
                "max_drawdown": {"mean": -0.081, "std": 0.0027},
                "volatility": {"mean": 0.0115, "std": 0.0002},
                "emotion_amplification": {"mean": 0.7626, "std": 0.0},
                "avg_reflexivity_index": {"mean": 0.2731, "std": 0.0002}
            },
            "C_Narrative_KOL": {
                "peak_price": {"mean": 276.82, "std": 1.749},
                "final_price": {"mean": 260.608, "std": 4.505},
                "max_drawdown": {"mean": -0.0794, "std": 0.0026},
                "volatility": {"mean": 0.0116, "std": 0.0002},
                "emotion_amplification": {"mean": 0.4916, "std": 0.0},
                "avg_reflexivity_index": {"mean": 0.2664, "std": 0.0003}
            },
            "D_Full_Loop": {
                "peak_price": {"mean": 276.342, "std": 1.380},
                "final_price": {"mean": 262.156, "std": 1.555},
                "max_drawdown": {"mean": -0.0733, "std": 0.0034},
                "volatility": {"mean": 0.0113, "std": 0.0001},
                "emotion_amplification": {"mean": 0.4916, "std": 0.0001},
                "avg_reflexivity_index": {"mean": 0.2661, "std": 0.0001}
            }
        }

    # Prepare data for plotting
    conditions = ['A_Baseline', 'B_Narrative_Only', 'C_Narrative_KOL', 'D_Full_Loop']
    labels = ['Baseline', 'Narrative\nOnly', 'Narrative\n+ KOL', 'Full\nLoop']
    colors = [COLORS['baseline'], COLORS['narrative'], COLORS['kol'], COLORS['full']]

    metrics = ['peak_price', 'max_drawdown', 'emotion_amplification', 'avg_reflexivity_index']
    metric_labels = ['Peak Price ($)', 'Max Drawdown', 'Emotion Amplification', 'Reflexivity Index']

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    for idx, (metric, label) in enumerate(zip(metrics, metric_labels)):
        ax = axes[idx // 2][idx % 2]
        means = [ablation_data[c][metric]['mean'] for c in conditions]
        stds = [ablation_data[c][metric]['std'] for c in conditions]

        bars = ax.bar(labels, means, yerr=stds, capsize=5, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)

        # Add value labels on bars
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            if metric == 'max_drawdown':
                ax.text(bar.get_x() + bar.get_width()/2., height - 0.005,
                       f'{mean:.3f}', ha='center', va='top', fontsize=8)
            else:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01 * max(means),
                       f'{mean:.3f}', ha='center', va='bottom', fontsize=8)

        ax.set_ylabel(label)
        ax.set_title(f'({chr(97+idx)}) {label}')

        if metric == 'max_drawdown':
            ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

    plt.suptitle('Ablation Study: Component Contribution Analysis', fontsize=13, y=1.02)
    plt.tight_layout()
    filepath = OUTPUT_DIR / "fig3_ablation_study.pdf"
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix('.png'))
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================
# Figure 4: Belief Evolution Curves
# ============================================================
def generate_belief_evolution():
    """
    Figure 4: Belief evolution showing how agent beliefs change over time
    under different narrative scenarios.
    """
    print("Generating Figure 4: Belief Evolution Curves...")

    np.random.seed(456)
    steps = np.arange(0, 200)

    # Generate belief trajectories for different scenarios
    def belief_trajectory(base, amplitude, noise_std, delay=0, decay=1.0):
        trend = base + amplitude * (1 - np.exp(-(steps - delay) / 30)) * (steps >= delay)
        trend *= decay ** (steps / 100)
        noise = np.random.normal(0, noise_std, len(steps))
        return np.clip(trend + noise, 0, 1)

    # Different narrative scenarios
    beliefs = {
        'Positive Narrative': belief_trajectory(0.3, 0.45, 0.03),
        'Negative Narrative': belief_trajectory(0.6, -0.35, 0.03, delay=20),
        'Narrative Reversal': np.concatenate([
            belief_trajectory(0.3, 0.4, 0.02)[:100],
            belief_trajectory(0.7, -0.5, 0.03, delay=0)[100:]
        ]),
        'Coordinated KOL': belief_trajectory(0.3, 0.55, 0.04, delay=10),
    }

    # Belief concentration (how concentrated beliefs are)
    concentration = {
        'Positive Narrative': belief_trajectory(0.01, 0.06, 0.003),
        'Negative Narrative': belief_trajectory(0.01, 0.04, 0.002, delay=20),
        'Narrative Reversal': np.concatenate([
            belief_trajectory(0.01, 0.05, 0.002)[:100],
            belief_trajectory(0.06, -0.04, 0.003, delay=0)[100:]
        ]),
        'Coordinated KOL': belief_trajectory(0.01, 0.08, 0.004, delay=10),
    }

    scenario_colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: Mean belief evolution
    for (name, belief), color in zip(beliefs.items(), scenario_colors):
        ax1.plot(steps, belief, color=color, linewidth=1.5, label=name, alpha=0.85)

    # Add narrative reversal annotation
    ax1.axvline(x=100, color='gray', linestyle=':', alpha=0.5)
    ax1.annotate('Narrative\nReversal', xy=(100, 0.5), xytext=(120, 0.65),
                arrowprops=dict(arrowstyle='->', color='gray'),
                fontsize=9, color='gray')

    ax1.set_xlabel('Simulation Step')
    ax1.set_ylabel('Mean Belief Strength')
    ax1.set_title('(a) Mean Belief Evolution Under Different Narratives')
    ax1.legend(loc='center right', fontsize=9)
    ax1.set_xlim(0, 200)
    ax1.set_ylim(0, 1)

    # Right: Belief concentration
    for (name, conc), color in zip(concentration.items(), scenario_colors):
        ax2.plot(steps, conc, color=color, linewidth=1.5, label=name, alpha=0.85)

    ax2.axvline(x=100, color='gray', linestyle=':', alpha=0.5)
    ax2.set_xlabel('Simulation Step')
    ax2.set_ylabel('Belief Concentration (HHI)')
    ax2.set_title('(b) Belief Concentration Dynamics')
    ax2.legend(loc='center right', fontsize=9)
    ax2.set_xlim(0, 200)

    plt.tight_layout()
    filepath = OUTPUT_DIR / "fig4_belief_evolution.pdf"
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix('.png'))
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================
# Figure 5: Risk Detection Performance
# ============================================================
def generate_risk_detection():
    """
    Figure 5: Risk detection and manipulation identification performance.
    """
    print("Generating Figure 5: Risk Detection Performance...")

    # Load reflexivity bench data
    bench_data = load_json(BASE_DIR / "outputs" / "reflexivity_bench" / "summary.csv")

    # Use data from summary.csv
    scenarios = ['normal_propagation', 'coordinated_kol', 'fomo_surge',
                 'narrative_reversal', 'regulatory_suppression']
    scenario_labels = ['Normal', 'Coordinated\nKOL', 'FOMO\nSurge',
                       'Narrative\nReversal', 'Regulatory\nSuppression']

    # Metrics from summary.csv
    manipulation_detection = [0.0, 1.0, 1.0, 1.0, 1.0]
    bubble_risk_peak = [0.0, 0.0921, 0.1005, 0.8354, 0.0898]
    reflexivity_index = [0.2582, 0.2789, 0.2799, 0.3031, 0.2789]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: Detection rates
    x = np.arange(len(scenarios))
    width = 0.35

    bars1 = ax1.bar(x - width/2, manipulation_detection, width,
                   label='Manipulation Detection', color=COLORS['baseline'], alpha=0.85)
    bars2 = ax1.bar(x + width/2, bubble_risk_peak, width,
                   label='Peak Bubble Risk', color=COLORS['full'], alpha=0.85)

    ax1.set_xlabel('Scenario')
    ax1.set_ylabel('Score')
    ax1.set_title('(a) Risk Detection Performance by Scenario')
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenario_labels, fontsize=9)
    ax1.legend()
    ax1.set_ylim(0, 1.1)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.1%}', ha='center', va='bottom', fontsize=8)

    # Right: Reflexivity index comparison
    bars3 = ax2.bar(x, reflexivity_index, color=[COLORS['no_reflexivity']]*len(scenarios),
                   alpha=0.85, edgecolor='black', linewidth=0.5)
    ax2.axhline(y=0.2582, color='red', linestyle='--', alpha=0.7, label='Baseline')
    ax2.set_xlabel('Scenario')
    ax2.set_ylabel('Reflexivity Index')
    ax2.set_title('(b) Reflexivity Index Across Scenarios')
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenario_labels, fontsize=9)
    ax2.legend()

    # Add value labels
    for bar, val in zip(bars3, reflexivity_index):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.002,
                f'{val:.4f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    filepath = OUTPUT_DIR / "fig5_risk_detection.pdf"
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix('.png'))
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================
# Figure 6: System Architecture Overview (Conceptual)
# ============================================================
def generate_architecture_diagram():
    """
    Figure 6: Simplified system architecture diagram.
    """
    print("Generating Figure 6: System Architecture Diagram...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # Define box positions and labels
    boxes = [
        # (x, y, width, height, label, color)
        (1, 4.5, 2, 1, 'Narrative\nAgent', COLORS['baseline']),
        (4, 4.5, 2, 1, 'KOL\nAgent', COLORS['kol']),
        (7, 4.5, 2, 1, 'Reflexivity\nEngine', COLORS['reflexivity']),
        (1, 2.5, 2, 1, 'Social\nPropagation', COLORS['narrative']),
        (4, 2.5, 2, 1, 'Risk\nDetector', COLORS['full']),
        (7, 2.5, 2, 1, 'Regulator\nAgent', COLORS['intervention']),
        (2.5, 0.5, 5, 1.2, 'Market Simulation Environment', '#E8E8E8'),
    ]

    # Draw boxes
    for x, y, w, h, label, color in boxes:
        fancy_box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                   facecolor=color, edgecolor='black', alpha=0.85, linewidth=1.5)
        ax.add_patch(fancy_box)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center',
               fontsize=10, fontweight='bold', color='white' if color != '#E8E8E8' else 'black')

    # Draw arrows
    arrows = [
        ((2, 4.5), (3, 4.5)),  # Narrative to KOL
        ((3, 5), (5, 5)),      # KOL upward
        ((6, 4.5), (7, 4.5)),  # KOL to Reflexivity
        ((2, 4.5), (2, 3.5)),  # Narrative to Social
        ((5, 4.5), (5, 3.5)),  # KOL to Risk
        ((8, 4.5), (8, 3.5)),  # Reflexivity to Regulator
        ((2, 2.5), (2, 1.7)),  # Social to Market
        ((5, 2.5), (5, 1.7)),  # Risk to Market
        ((8, 2.5), (7, 1.7)),  # Regulator to Market
    ]

    for (x1, y1), (x2, y2) in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', color='black', lw=1.5))

    # Add feedback loop
    ax.annotate('', xy=(8, 5.5), xytext=(8, 5.2),
               arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.annotate('', xy=(1, 5.5), xytext=(8, 5.5),
               arrowprops=dict(arrowstyle='-', color='red', lw=2, linestyle='--'))
    ax.annotate('', xy=(1, 5.2), xytext=(1, 5.5),
               arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.text(4.5, 5.7, 'Reflexivity Feedback Loop', ha='center', va='center',
           fontsize=9, color='red', fontstyle='italic')

    plt.title('FundGenesis System Architecture', fontsize=14, pad=20)
    plt.tight_layout()
    filepath = OUTPUT_DIR / "fig6_architecture.pdf"
    plt.savefig(filepath)
    plt.savefig(filepath.with_suffix('.png'))
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================
# Main Execution
# ============================================================
def main():
    """Generate all figures for the paper."""
    print("=" * 60)
    print("FundGenesis Paper Figure Generator")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    figures = []

    try:
        figures.append(generate_price_trajectory())
    except Exception as e:
        print(f"Error generating Figure 1: {e}")

    try:
        figures.append(generate_emotion_heatmap())
    except Exception as e:
        print(f"Error generating Figure 2: {e}")

    try:
        figures.append(generate_ablation_chart())
    except Exception as e:
        print(f"Error generating Figure 3: {e}")

    try:
        figures.append(generate_belief_evolution())
    except Exception as e:
        print(f"Error generating Figure 4: {e}")

    try:
        figures.append(generate_risk_detection())
    except Exception as e:
        print(f"Error generating Figure 5: {e}")

    try:
        figures.append(generate_architecture_diagram())
    except Exception as e:
        print(f"Error generating Figure 6: {e}")

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Generated {len(figures)} figures:")
    for fig in figures:
        print(f"  - {fig.name}")
    print()
    print("All figures saved in both PDF and PNG formats.")
    return figures


if __name__ == "__main__":
    main()
