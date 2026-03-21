"""Example: 개별 플롯 예제 (한글 지원).

dartwork-mpl을 사용한 깔끔하고 전문적인 개별 플롯 생성
대시보드/다중 플롯의 복잡성 없이 단일 플롯에 집중

실행:
    uv run python examples/single_plot_korean.py
"""

import matplotlib.pyplot as plt
import numpy as np
import dartwork_mpl as dm

def example_line_plot():
    """SI 단위 포매팅을 사용한 라인 플롯."""
    dm.style.use("report-kr")  # 한글 지원 스타일

    # 그림 생성
    fig, ax = dm.subplots(figsize=dm.FS_SINGLE)

    # 데이터 생성
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x) * 1.5e6
    y2 = np.cos(x) * 1.2e6

    # 플롯
    ax.plot(x, y1, label='신호 A', linewidth=2)
    ax.plot(x, y2, label='신호 B', linewidth=2)

    # 포매팅 적용
    dm.format_axis_si(ax, axis='y')  # SI 접두사 포매팅
    dm.minimal_axes(ax)  # 깔끔한 외관

    # 라벨
    ax.set_xlabel('시간 (초)')
    ax.set_ylabel('진폭')
    ax.set_title('신호 분석')
    ax.legend(loc='upper right')

    # 그리드
    dm.add_grid(ax, which='major', alpha=0.2)

    plt.tight_layout()
    plt.savefig('output/line_plot_kr.png', dpi=300)
    print("  ✅ 라인 플롯 저장: line_plot_kr.png")
    plt.close()

def example_bar_plot():
    """값 레이블이 있는 막대 그래프."""
    dm.style.use("report-kr")

    # 그림 생성
    fig, ax = dm.subplots(figsize=dm.FS_WIDE)

    # 데이터
    categories = ['1분기', '2분기', '3분기', '4분기']
    values = [1200000, 1450000, 1380000, 1620000]

    # 플롯
    bars = ax.bar(categories, values, color='#1f77b4')

    # y축 백만 단위 포매팅
    dm.format_axis_millions(ax, axis='y')

    # 막대 위에 값 레이블 추가
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{value/1e6:.1f}M원',
                ha='center', va='bottom')

    # 스타일 정리
    dm.hide_spines(ax, ['top', 'right'])
    ax.set_ylabel('매출액')
    ax.set_title('분기별 매출 실적')

    plt.tight_layout()
    plt.savefig('output/bar_plot_kr.png', dpi=300)
    print("  ✅ 막대 그래프 저장: bar_plot_kr.png")
    plt.close()

def example_scatter_plot():
    """회귀선이 있는 산점도."""
    dm.style.use("report-kr")

    # 그림 생성
    fig, ax = dm.subplots(figsize=dm.FS_SQUARE)

    # 데이터 생성
    np.random.seed(42)
    x = np.random.randn(50) * 10 + 50
    y = 2 * x + np.random.randn(50) * 15 + 100

    # 산점도
    ax.scatter(x, y, alpha=0.6, s=50, label='데이터 포인트')

    # 회귀선 추가
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_line, p(x_line), 'r--', alpha=0.8,
            label=f'회귀선: y = {z[0]:.1f}x + {z[1]:.1f}')

    # 스타일
    dm.add_grid(ax, alpha=0.15)
    ax.set_xlabel('독립 변수')
    ax.set_ylabel('종속 변수')
    ax.set_title('상관관계 분석')
    ax.legend()

    plt.tight_layout()
    plt.savefig('output/scatter_plot_kr.png', dpi=300)
    print("  ✅ 산점도 저장: scatter_plot_kr.png")
    plt.close()

def example_histogram():
    """정규분포 오버레이가 있는 히스토그램."""
    dm.style.use("report-kr")

    # 그림 생성
    fig, ax = dm.subplots(figsize=dm.FS_SINGLE)

    # 데이터 생성
    np.random.seed(42)
    data = np.random.normal(100, 15, 1000)

    # 히스토그램
    n, bins, patches = ax.hist(data, bins=30, density=True,
                                alpha=0.7, edgecolor='black',
                                linewidth=0.5, label='관측 데이터')

    # 정규분포 오버레이 추가
    from scipy import stats
    mu, std = data.mean(), data.std()
    xmin, xmax = ax.get_xlim()
    x = np.linspace(xmin, xmax, 100)
    p = stats.norm.pdf(x, mu, std)
    ax.plot(x, p, 'r-', linewidth=2,
            label=f'정규분포\n평균={mu:.1f}, 표준편차={std:.1f}')

    # 포매팅
    ax.set_xlabel('값')
    ax.set_ylabel('확률 밀도')
    ax.set_title('분포 분석')
    ax.legend()

    plt.tight_layout()
    plt.savefig('output/histogram_kr.png', dpi=300)
    print("  ✅ 히스토그램 저장: histogram_kr.png")
    plt.close()

def example_pie_chart():
    """도넛 차트 스타일의 파이 차트."""
    dm.style.use("report-kr")

    # 그림 생성
    fig, ax = dm.subplots(figsize=dm.FS_SQUARE)

    # 데이터
    sizes = [35, 30, 20, 10, 5]
    labels = ['제품A', '제품B', '제품C', '제품D', '기타']
    colors = ['#2E86C1', '#E74C3C', '#48C9B0', '#F39C12', '#9B59B6']

    # 파이 차트
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90,
        pctdistance=0.85
    )

    # 도넛 홀 추가
    circle = plt.Circle((0, 0), 0.70, fc='white')
    ax.add_artist(circle)

    # 중앙 텍스트
    ax.text(0, 0, '제품별\n매출 비중', ha='center', va='center',
            fontsize=14, fontweight='bold')

    # 퍼센트 텍스트 스타일
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')

    ax.set_title('2024년 제품별 매출 구성')

    plt.tight_layout()
    plt.savefig('output/pie_chart_kr.png', dpi=300)
    print("  ✅ 파이 차트 저장: pie_chart_kr.png")
    plt.close()

def example_time_series():
    """시계열 데이터 플롯."""
    dm.style.use("report-kr")

    # 그림 생성
    fig, ax = dm.subplots(figsize=dm.FS_WIDE)

    # 시계열 데이터 생성
    dates = np.arange('2024-01', '2025-01', dtype='datetime64[M]')
    revenue = np.array([120, 135, 128, 142, 155, 148, 162, 175, 168, 182, 195, 210])
    profit = revenue * 0.15 + np.random.randn(12) * 5

    # 이중 축 플롯
    ax.bar(dates, revenue, alpha=0.3, label='매출액', color='skyblue')
    ax.set_xlabel('월')
    ax.set_ylabel('매출액 (백만원)', color='blue')
    ax.tick_params(axis='y', labelcolor='blue')

    ax2 = ax.twinx()
    ax2.plot(dates, profit, color='green', marker='o', linewidth=2, label='영업이익')
    ax2.set_ylabel('영업이익 (백만원)', color='green')
    ax2.tick_params(axis='y', labelcolor='green')

    # 타이틀과 그리드
    ax.set_title('2024년 월별 실적 추이')
    ax.grid(True, alpha=0.3)

    # 범례
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc='upper left')

    plt.tight_layout()
    plt.savefig('output/time_series_kr.png', dpi=300)
    print("  ✅ 시계열 플롯 저장: time_series_kr.png")
    plt.close()

if __name__ == "__main__":
    print("🎨 dartwork-mpl 개별 플롯 예제 (한글 지원)")
    print("=" * 50)

    print("\n1. 라인 플롯 (SI 단위 포매팅)...")
    example_line_plot()

    print("\n2. 막대 그래프 (값 레이블)...")
    example_bar_plot()

    print("\n3. 산점도 (회귀선)...")
    example_scatter_plot()

    print("\n4. 히스토그램 (정규분포)...")
    example_histogram()

    print("\n5. 파이 차트 (도넛 스타일)...")
    example_pie_chart()

    print("\n6. 시계열 플롯 (이중 축)...")
    example_time_series()

    print("\n" + "=" * 50)
    print("✅ 모든 개별 플롯 예제 완료!")
    print("📁 출력 위치: output/")