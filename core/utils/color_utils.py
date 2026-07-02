def adjust_color_brightness(color, factor):
    """调整颜色亮度"""
    try:
        # 移除#号
        if color.startswith('#'):
            color = color[1:]
        
        # 转换为RGB
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        
        # 调整亮度
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        
        # 转换回十六进制
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        # 如果转换失败，返回默认颜色
        return "#555" if factor > 1 else "#333"


def lighten_color(color_hex):
    """使颜色变亮"""
    try:
        # 移除#号
        color_hex = color_hex.lstrip('#')
        # 转换为RGB
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        # 增加亮度
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return color_hex


def darken_color(color_hex):
    """使颜色变暗"""
    try:
        # 移除#号
        color_hex = color_hex.lstrip('#')
        # 转换为RGB
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        # 降低亮度
        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return color_hex
