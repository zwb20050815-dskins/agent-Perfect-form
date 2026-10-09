"""第九课9.1：通过 MCP 提供原来的贴现计算器。stdout只用于协议。"""

from typing import Annotated

from mcp.server import MCPServer
from pydantic import BaseModel, Field

from lesson07a import calculate_discount_interest as local_calculator

mcp = MCPServer("knowledge-agent-calculator", log_level="WARNING")


class DiscountResult(BaseModel):
    interest_yuan: str
    face_value: float
    annual_rate_percent: float
    days: int
    year_days: int


@mcp.tool()
def calculate_discount_interest(
    face_value: Annotated[float, Field(strict=True, gt=0, le=1_000_000_000_000, description="票面金额，单位：元")],
    annual_rate_percent: Annotated[float, Field(strict=True, ge=0, le=100, description="年贴现率的百分数，3表示3%")],
    days: Annotated[int, Field(strict=True, ge=0, le=3660, description="剩余贴现天数，整数")],
) -> DiscountResult:
    """按一年360天计算贴现利息，四舍五入到分；只接受金额、年贴现率百分数和整数天数。"""
    # 计算规则沿用第七课，只把调用入口改成MCP。这里在服务端进程执行。
    result = local_calculator.invoke({"face_value": face_value,
                                      "annual_rate_percent": annual_rate_percent, "days": days})
    return DiscountResult(**result)


if __name__ == "__main__":
    # 服务端不要print到stdout，会干扰JSON-RPC消息；调试可输出到sys.stderr。
    mcp.run(transport="stdio")
