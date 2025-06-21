import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
import warnings
from ta.volatility import AverageTrueRange
import plotly.graph_objects as go
import plotly.io as pio

def plot_chart_with_levels(
    df,
    levels,
    trend_info=None,
    patterns=None,
    risk_info=None,
    save_file=None,
    show_atr=True,
    show_bollinger=True,
    interactive=False
):
    df = df.copy()
    required_cols = ['Open', 'High', 'Low', 'Close']
    if 'Volume' in df.columns:
        required_cols.append('Volume')
    df = df[required_cols]
    df.index = pd.to_datetime(df.index)
    df.index.name = 'Date'

    # --- If Plotly Interactive Chart ---
    if interactive:
        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Candles'
        ))

        # Support/Resistance
        for s in levels['support']:
            fig.add_hline(y=s['price'], line_color='green', line_dash='dash', opacity=0.5)
        for r in levels['resistance']:
            fig.add_hline(y=r['price'], line_color='red', line_dash='dash', opacity=0.5)

        # Bollinger Bands
        if show_bollinger and len(df) >= 20:
            mid = df['Close'].rolling(20).mean()
            std = df['Close'].rolling(20).std()
            fig.add_trace(go.Scatter(x=df.index, y=mid + 2*std, name="Upper BB", line=dict(color='cyan', dash='dot')))
            fig.add_trace(go.Scatter(x=df.index, y=mid - 2*std, name="Lower BB", line=dict(color='cyan', dash='dot')))

        # ATR Bands
        if show_atr and len(df) >= 14:
            atr = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14)
            atr_val = atr.average_true_range()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'] + atr_val, name="Upper ATR", line=dict(color='purple')))
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'] - atr_val, name="Lower ATR", line=dict(color='purple')))

        # Final layout
        fig.update_layout(
            title="Forex Chart (Plotly)",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_white",
            showlegend=True
        )

        # Save
        html_file = save_file.replace(".png", ".html") if save_file else "interactive_chart.html"
        pio.write_html(fig, file=html_file, auto_open=False)
        print(f"📊 Plotly chart saved as: {html_file}")
        return

    # --- MPLFinance Mode ---
    hlines = [s['price'] for s in levels['support']] + [r['price'] for r in levels['resistance']]
    colors = ['green'] * len(levels['support']) + ['red'] * len(levels['resistance'])
    hline_styles = dict(hlines=hlines, colors=colors, linestyle='--', linewidths=1)

    extra_lines = []
    label_points = []

    if risk_info:
        if 'entry_zone' in risk_info:
            entry_range = risk_info['entry_zone'].split(' - ')
            entry_mid = round((float(entry_range[0]) + float(entry_range[1])) / 2, 5)
            extra_lines.append(mpf.make_addplot([entry_mid]*len(df), color='blue', linestyle='--', width=1))
            label_points.append((entry_mid, 'Entry', 'blue'))

            sl = risk_info.get('stop_loss')
            if sl:
                extra_lines.append(mpf.make_addplot([sl]*len(df), color='red', linestyle='-', width=1))
                label_points.append((sl, 'Stop Loss', 'red'))

            for i, tp in enumerate(risk_info.get('take_profit_levels', []), 1):
                extra_lines.append(mpf.make_addplot([tp]*len(df), color='green', linestyle='-', width=1))
                label_points.append((tp, f'TP{i}', 'green'))

            trail = risk_info.get("trailing_stop_suggestion")
            if trail:
                extra_lines.append(mpf.make_addplot([trail]*len(df), color='orange', linestyle=':', width=1))
                label_points.append((trail, 'Trailing SL', 'orange'))

        elif 'note' in risk_info:
            label_points.append((df['Close'].iloc[-1], f"⚠️ {risk_info['note']}", 'orange'))

    # --- ATR Band Overlay ---
    if show_atr and len(df) >= 14:
        atr = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14)
        atr_val = atr.average_true_range()
        extra_lines.append(mpf.make_addplot(df['Close'] + atr_val, color='purple', linestyle=':', width=1))
        extra_lines.append(mpf.make_addplot(df['Close'] - atr_val, color='purple', linestyle=':', width=1))

    # --- Bollinger Bands ---
    if show_bollinger and len(df) >= 20:
        mid = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        extra_lines.append(mpf.make_addplot(mid + 2*std, color='cyan', linestyle='--', width=1))
        extra_lines.append(mpf.make_addplot(mid - 2*std, color='cyan', linestyle='--', width=1))

    plot_args = dict(
        data=df.tail(300),
        type='candle',
        style='yahoo',
        title='Forex Chart with Key Levels',
        ylabel='Price',
        hlines=hline_styles,
        addplot=extra_lines,
        returnfig=True
    )
    if save_file:
        plot_args['savefig'] = save_file

    fig, axes = mpf.plot(**plot_args)
    ax = axes[0]
    x_pos = df.tail(100).index[-1]

    for price, label, color in label_points:
        ax.annotate(
            f"{label}",
            xy=(x_pos, price),
            xytext=(x_pos, price),
            textcoords="offset points",
            xycoords='data',
            color=color,
            fontsize=8,
            ha='left',
            va='center',
            bbox=dict(boxstyle="round,pad=0.2", fc='white', ec=color, lw=1, alpha=0.6)
        )

    from matplotlib.lines import Line2D
    legend_items = [
        Line2D([0], [0], color='green', linestyle='--', label='Support'),
        Line2D([0], [0], color='red', linestyle='--', label='Resistance'),
        Line2D([0], [0], color='purple', linestyle=':', label='ATR Bands'),
        Line2D([0], [0], color='cyan', linestyle='--', label='Bollinger Bands'),
        Line2D([0], [0], color='blue', linestyle='--', label='Entry'),
        Line2D([0], [0], color='red', linestyle='-', label='Stop Loss'),
        Line2D([0], [0], color='green', linestyle='-', label='Take Profit'),
        Line2D([0], [0], color='orange', linestyle=':', label='Trailing SL')
    ]
    ax.legend(handles=legend_items, loc='upper left', fontsize=8, framealpha=0.6)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        fig.tight_layout()

    plt.show()
