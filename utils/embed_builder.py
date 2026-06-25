import discord

def build_simple_embed(title: str, description: str = "", color=discord.Color.blurple()) -> discord.Embed:
    """
    봇 전체에서 일관된 디자인의 Embed를 생성하기 위한 헬퍼 함수입니다.
    """
    embed = discord.Embed(
        title=title, 
        description=description, 
        color=color
    )

    embed.set_footer(text="개발자 : mediblo")
    return embed