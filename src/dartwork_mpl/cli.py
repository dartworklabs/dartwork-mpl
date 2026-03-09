#!/usr/bin/env python3
"""dartwork-mpl MCP 서버용 명령줄 인터페이스(CLI) 모듈.

이 모듈은 dartwork-mpl 모델 컨텍스트 프로토콜(MCP) 서버를
실행하기 위한 명령줄 진입점을 제공합니다.
"""

__all__ = ["main"]

from .mcp.server import mcp


def main() -> None:
    """dartwork-mpl MCP 서버를 실행합니다.

    이 함수는 모델 컨텍스트 프로토콜(MCP)을 통해 dartwork-mpl의
    사용 가이드와 문서를 에이전트 환경에 연동하는 FastMCP 서버를 시작합니다.
    """
    mcp.run()


if __name__ == "__main__":
    main()
