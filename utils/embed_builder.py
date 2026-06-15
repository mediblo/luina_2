import discord

def build_simple_embed(title: str, description: str, color=discord.Color.blue()) -> discord.Embed:
    """
    봇 전체에서 일관된 디자인의 Embed를 생성하기 위한 헬퍼 함수입니다.
    나중에 봇의 메인 테마 색상이 바뀌어도 이 함수 한 곳만 수정하면 됩니다.
    """
    return discord.Embed(
        title=title, 
        description=description, 
        color=color
    )