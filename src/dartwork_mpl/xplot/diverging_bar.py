"""발산형(Diverging) 바 차트 시각화 모듈.

중앙 축을 기준으로 양수와 음수 값을 반대 방향으로 표시하는 발산형 바 차트를
생성하는 기능을 제공합니다.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import blended_transform_factory

import dartwork_mpl as dm


def plot_diverging_bar(
    labels: list[str] | None = None,
    neg_values: np.ndarray | None = None,
    pos_values: np.ndarray | None = None,
    add_total: bool = True,
    figsize: tuple[float, float] | None = None,
    dpi: int = 300,
    title: str | None = None,
    neg_label: str = "Review & Refactoring overhead",
    pos_label: str = "Code Generation savings",
    colors: dict[str, str] | None = None,
    hbar_height: float = 0.5,
    hbar_spacing_factor: float = 1.6,
    left_margin: float = 0.35,
    right_margin: float = 0.95,
    figure_bottom: float = 0.03,
    base_x: float = 0.02,
    title_y: float = 0.95,
    title_to_legend_gap: float = 0.05,
    legend_to_figure_gap: float = 0.06,
) -> tuple[Figure, Axes]:
    """양수와 음수 값을 가지는 발산형(diverging) 바 차트를 생성합니다.

    이 함수는 중앙 축을 기준으로 음수는 왼쪽으로, 양수는 오른쪽으로 뻗어나가는
    가로형 바 차트를 생성합니다. 제목, 범례, 피규어가 세로로 배치되는
    계단식(cascading) 레이아웃을 사용합니다.

    Parameters
    ----------
    labels : list[str] | None, optional
        차트 왼쪽에 표시될 카테고리 라벨 리스트. 라벨은 위에서 아래로 역순으로
        표시됩니다. None인 경우 기본 샘플 데이터를 사용합니다. 기본값은 None.
    neg_values : np.ndarray | None, optional
        음수 값 배열 (라벨당 하나). 값은 음수여야 합니다. None인 경우
        기본 샘플 데이터를 사용합니다. 기본값은 None.
    pos_values : np.ndarray | None, optional
        양수 값 배열 (라벨당 하나). 값은 양수여야 합니다. None인 경우
        기본 샘플 데이터를 사용합니다. 기본값은 None.
    add_total : bool, optional
        True이면 평균값을 포함하는 "Total" 행을 추가합니다. 기본값은 True.
    figsize : tuple[float, float] | None, optional
        피규어 크기 (너비, 높이) 인치 단위. None인 경우 (12cm, 12cm)를
        사용합니다. 기본값은 None.
    dpi : int, optional
        피규어 해상도 (인치당 도트 수). 기본값은 300.
    title : str | None, optional
        상단에 표시될 제목 텍스트. None인 경우 기본 제목을 사용합니다.
        기본값은 None.
    neg_label : str, optional
        범례(legend)에 표시될 음수 바의 라벨.
        기본값은 "Review & Refactoring overhead".
    pos_label : str, optional
        범례(legend)에 표시될 양수 바의 라벨.
        기본값은 "Code Generation savings".
    colors : dict[str, str] | None, optional
        'neg'와 'pos' 키를 가지는 색상 딕셔너리. None인 경우 기본 색상
        (음수는 MidnightBlue 계열, 양수는 CornflowerBlue 계열)을
        사용합니다. 기본값은 None.
    hbar_height : float, optional
        각 가로 바의 높이. 기본값은 0.5.
    hbar_spacing_factor : float, optional
        ``hbar_height``의 배수로 나타낸 바 사이의 간격. 기본값은 1.6.
    left_margin : float, optional
        피규어 좌표계(0-1) 기준 Axes의 왼쪽 여백. 기본값은 0.35.
    right_margin : float, optional
        피규어 좌표계(0-1) 기준 Axes의 오른쪽 여백. 기본값은 0.95.
    figure_bottom : float, optional
        피규어 좌표계(0-1) 기준 Axes의 아래쪽 여백. 기본값은 0.03.
    base_x : float, optional
        피규어 좌표계(0-1) 기준 제목, 범례, 라벨의 공통 x 좌표.
        기본값은 0.02.
    title_y : float, optional
        피규어 좌표계(0-1) 기준 제목의 시작 y 좌표. 기본값은 0.95.
    title_to_legend_gap : float, optional
        피규어 좌표계(0-1) 기준 제목과 범례 사이의 간격. 기본값은 0.05.
    legend_to_figure_gap : float, optional
        피규어 좌표계(0-1) 기준 범례와 피규어 사이의 간격. 기본값은 0.06.

    Returns
    -------
    fig : matplotlib.figure.Figure
        생성된 피규어 객체.
    ax : matplotlib.axes.Axes
        차트가 포함된 Axes 객체.

    Examples
    --------
    >>> import numpy as np
    >>> import dartwork_mpl as dm
    >>> dm.style.use('scientific')
    >>>
    >>> # 최소한의 설정 - 기본 샘플 데이터 사용
    >>> fig, ax = plot_diverging_bar()
    >>> dm.save_and_show(fig)
    >>>
    >>> # 커스텀 데이터 사용
    >>> labels = [
    ...     "Frontend Development",
    ...     "Backend Architecture",
    ...     "Data Engineering",
    ...     "API Integration",
    ...     "Quality Assurance",
    ...     "DevOps & Infrastructure",
    ...     "Security Compliance",
    ...     "Technical Documentation",
    ... ]
    >>> neg_values = np.array([-5, -8, -10, -10, -8, -9, -10, -7])
    >>> pos_values = np.array([20, 35, 32, 40, 20, 28, 38, 30])
    >>> fig, ax = plot_diverging_bar(
    ...     labels,
    ...     neg_values,
    ...     pos_values
    ... )
    >>> dm.save_and_show(fig)
    >>>
    >>> # Total 행 없이 제목 및 색상 커스터마이징
    >>> fig, ax = plot_diverging_bar(
    ...     labels,
    ...     neg_values,
    ...     pos_values,
    ...     add_total=False,
    ...     title="Custom Title",
    ...     colors={'neg': 'oc.red5', 'pos': 'oc.green5'}
    ... )
    >>> dm.save_and_show(fig)

    Notes
    -----
    - 이 함수는 제목, 범례, 차트가 위에서 아래로 자동 간격을 두고
      배치되는 계단식(cascading) 레이아웃을 사용합니다.
    - 라벨은 ``blended_transform_factory``를 사용하여 피규어의 x 좌표와
      데이터의 y 좌표를 혼합하여 배치됩니다.
    - "Total" 행(활성화된 경우)은 자동으로 ``dm.fw(1)``이 적용되어 굵게 표시됩니다.
    - 값 라벨은 바 안에 위치합니다 (음수는 왼쪽, 양수는 오른쪽).

    See Also
    --------
    dartwork_mpl.style.use : dartwork-mpl 스타일 프리셋 적용
    dartwork_mpl.simple_layout : 피규어 레이아웃 최적화
    matplotlib.transforms.blended_transform_factory : 혼합 좌표 변환 생성
    """
    # Use default sample data if not provided
    if labels is None:
        labels = [
            "Frontend Development",
            "Backend Architecture",
            "Data Engineering",
            "API Integration",
            "Quality Assurance",
            "DevOps & Infrastructure",
            "Security Compliance",
            "Technical Documentation",
        ]
    if neg_values is None:
        neg_values = np.array([-5, -8, -10, -10, -8, -9, -10, -7])
    if pos_values is None:
        pos_values = np.array([20, 35, 32, 40, 20, 28, 38, 30])

    # Prepare data: copy to avoid modifying input
    labels_list = labels.copy()
    neg_vals = neg_values.copy()
    pos_vals = pos_values.copy()

    # Add Total row if requested
    if add_total:
        labels_list.append("Total")
        neg_vals = np.append(neg_vals, np.mean(neg_vals))
        pos_vals = np.append(pos_vals, np.mean(pos_vals))

    # Reverse order for barh (top to bottom display)
    labels_list = labels_list[::-1]
    neg_vals = neg_vals[::-1]
    pos_vals = pos_vals[::-1]

    # Set default figure size using cm2in for unit conversion
    if figsize is None:
        figsize = (dm.cm2in(12), dm.cm2in(12))

    # Set default colors
    if colors is None:
        colors = {
            "neg": "#191970",  # MidnightBlue-like
            "pos": "#6495ED",  # CornflowerBlue-like
        }

    # Set default title
    if title is None:
        title = (
            "Engineering hours shifted by AI assistants, % of sprint capacity"
        )

    # Create figure with publication-ready settings
    fig = plt.figure(figsize=figsize, dpi=dpi)

    # Cascading layout calculation
    # Vertical positioning from top to bottom:
    # title_y -> legend_y -> figure_top
    legend_y = title_y - title_to_legend_gap
    figure_top = legend_y - legend_to_figure_gap

    # Set up GridSpec for precise layout control
    # left_margin reserves space for labels on the left
    # Labels are drawn at figure x=base_x (0.02)
    gs = fig.add_gridspec(
        nrows=1,
        ncols=1,
        left=left_margin,
        right=right_margin,
        top=figure_top,
        bottom=figure_bottom,
    )
    ax = fig.add_subplot(gs[0, 0])

    # Calculate y positions for bars
    # Spacing between bars = hbar_height * hbar_spacing_factor
    y_pos = np.arange(len(labels_list)) * hbar_height * hbar_spacing_factor

    # Plot horizontal bars
    # Negative values extend to the left
    bars_neg = ax.barh(
        y_pos,
        neg_vals,
        height=hbar_height,
        color=colors["neg"],
        label=neg_label,
    )
    # Positive values extend to the right
    bars_pos = ax.barh(
        y_pos,
        pos_vals,
        height=hbar_height,
        color=colors["pos"],
        label=pos_label,
    )

    # Styling: remove all spines and ticks
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # Remove x and y ticks
    ax.set_xticks([])
    ax.set_yticks([])

    # Add vertical grid line at x=0 for reference
    ax.axvline(0, color="lightgray", linewidth=0.8)

    # Create blended transform for labels
    # x-coordinate in figure space, y-coordinate in data space
    # This allows labels to be positioned at base_x (figure) while
    # aligning with bar positions (data)
    transform = blended_transform_factory(fig.transFigure, ax.transData)

    # Add text labels on the left side
    # Labels are positioned at base_x (figure x-coord) and y_pos (data
    # y-coord)
    for i, label in enumerate(labels_list):
        # Bold 'Total' label using dm.fw
        weight = dm.fw(1) if label == "Total" else dm.fw(0)

        ax.text(
            base_x,
            y_pos[i],
            label,
            ha="left",
            va="center",
            transform=transform,
            fontsize=dm.fs(0),
            fontweight=weight,
            wrap=True,
        )

    # Add value labels on bars
    # Negative values: label on the left side of the bar
    for rect in bars_neg:
        width = rect.get_width()
        ax.text(
            width - 1,  # Offset 1 unit to the left
            rect.get_y() + rect.get_height() / 2,  # Center vertically
            f"{int(width)}",
            ha="right",
            va="center",
            fontsize=dm.fs(-1),
        )

    # Positive values: label on the right side of the bar
    for rect in bars_pos:
        width = rect.get_width()
        ax.text(
            width + 1,  # Offset 1 unit to the right
            rect.get_y() + rect.get_height() / 2,  # Center vertically
            f"{int(width)}",
            ha="left",
            va="center",
            fontsize=dm.fs(-1),
        )

    # Add title at the top
    # Positioned at base_x (figure x-coord) and title_y (figure y-coord)
    fig.text(
        base_x,
        title_y,
        title,
        fontsize=dm.fs(2),
        fontweight=dm.fw(1),
        ha="left",
    )

    # Add custom legend
    # Positioned below title at base_x (figure x-coord) and legend_y
    # (figure y-coord)
    fig.legend(
        loc="upper left",
        bbox_to_anchor=(base_x, legend_y),
        ncol=2,
        frameon=False,
        fontsize=dm.fs(0),
        borderaxespad=0,
        columnspacing=1.5,
    )

    # Apply simple_layout for automatic margin optimization
    # Use bbox to optimize only the axes area, protecting title/legend
    # bbox format: (left, right, bottom, top) in figure coordinates
    # This ensures title (at title_y) and legend (at legend_y) are not
    # affected by the optimization
    # Use minimal settings to preserve original layout as much as possible:
    # - Zero margins to match original exactly
    # - Very low importance weights to minimize optimization
    # - Very small bound_margin to limit GridSpec parameter changes
    # - High gtol to allow early convergence
    dm.simple_layout(
        fig,
        gs=gs,
        bbox=(left_margin, right_margin, figure_bottom, figure_top),
        margins=(
            0.0,
            0.0,
            0.0,
            0.0,
        ),  # Zero margins to preserve original# Extremely low weights to minimize changes
        bound_margin=0.001,  # Very small bound margin to limit changes
        gtol=1e-1,  # Higher tolerance for early convergence
        use_all_axes=False,  # Only optimize axes in this GridSpec
    )

    return fig, ax


def get_source_code() -> str:
    """이 모듈의 소스 코드를 문자열 형식으로 반환합니다.

    이 함수는 코딩 에이전트(AI)에게 추가 개발이나 수정을 위한
    입력값으로 소스 코드를 제공할 때 사용됩니다.

    Returns
    -------
    str
        이 모듈의 전체 소스 코드.

    Examples
    --------
    >>> source = get_source_code()
    >>> print(source)
    """
    import importlib
    import inspect

    # Get the current module
    module_name = __name__
    module = importlib.import_module(module_name)

    # Get the source file path
    source_file = inspect.getfile(module)

    # Read and return the source code
    with open(source_file, encoding="utf-8") as f:
        return f.read()
