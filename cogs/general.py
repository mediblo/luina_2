import discord
from discord.ext import commands
from discord import app_commands

from collections import deque
from typing import Optional
import time
import random
import asyncio

from utils.embed_builder import build_simple_embed

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="정보", description="루이나에 대한 정보를 알려줍니다") # 정보 260616
    async def info(self, interaction: discord.Interaction):
        embed = build_simple_embed(
            title="정보",
            description="ℹ️ Luina V2.0"
        )
        #embed.set_thumbnail()

        embed.add_field(name= "개발자", value= "mediblo", inline=False)
        embed.add_field(name= "탄생일", value= "2020년 7월 26일")
        embed.add_field(name= "V2.0", value= "2026년 6월 15일", inline=False)
        embed.add_field(name= "제작자 이메일", value= "jjssog@naver.com\n-# 이메일은 자주 확인을 하지 않습니다.", inline=False)
        embed.add_field(name= "프로필 사진 출처", value= "None", inline=False)
        embed.add_field(name= "블로그 URL", value= "https://blog.naver.com/jjssog")
        embed.add_field(name= "Velog URL", value= "https://velog.io/@mediblo/posts")
        embed.set_footer(text= "오류나 건의사항은 제보해주시기 바랍니다")
        await interaction.response.send_message(embed= embed, ephemeral= True)

#########################################################################################################

    @app_commands.command(name="핑", description="퐁!") # 핑 - 퐁 260616
    async def ping(self, interaction: discord.Interaction):
        websocket_latency = round(self.bot.latency * 1000)
    
        # 2. 실제 응답 속도 계산을 위한 시작 시간 기록
        start_time = time.time()
        
        # 먼저 유저에게 생각을 유도하는 임시 메시지를 보냅니다.
        await interaction.response.send_message("🏓 퐁 측정 중...", ephemeral=True)
        
        # 3. 메시지가 전송된 후의 시간 계산
        end_time = time.time()
        response_latency = round((end_time - start_time) * 1000)
        
        # 이전에 만드신 build_simple_embed 헬퍼 함수가 있다면 활용하기 아주 좋습니다!
        embed = build_simple_embed(
            title="🏓 퐁! (Pong!)",
            description=(
                f"🌐 **웹소켓 지연 시간:** `{websocket_latency}ms`\n"
                f"⚡ **실제 응답 속도:** `{response_latency}ms`"
            ),
            color=discord.Color.green() # 성공적인 상태이므로 초록색 추천
        )
        
        # 임시로 보냈던 메시지를 Embed 메시지로 수정(Edit)합니다.
        await interaction.edit_original_response(content=None, embed=embed, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="계산기", description="일련의 식을 계산합니다.") # 계산기 260616
    @app_commands.describe(msg="일련의 식을 입력합니다 (2+4*4)")
    async def calculator(self, interaction: discord.Interaction, msg: str):

        def cal(num_a: float, num_b: float, op: str):
            operations = {
                "+": num_a + num_b,
                "-": num_a - num_b,
                "*": num_a * num_b,
                "/": num_a / num_b,
                "%": num_a % num_b
            }
            return operations.get(op, 0.0)

        # 연산자 우선순위 정의 (숫자가 높을수록 우선순위가 높음)
        # 괄호 '('는 스택 내부에서는 가장 낮은 우선순위를 가집니다.
        prec = {'*': 3, '/': 3, '%': 3, '+': 2, '-': 2, '(': 1}

        operator = []
        postfix = deque()

        temp = ""
        for x in msg:
            if x == ' ': 
                continue
            
            if x.isdigit() or x == '.':
                temp += x
            else:
                if temp:
                    postfix.append(float(temp))
                    temp = ""
                
                if x == '(':
                    operator.append(x)
                elif x == ')':
                    # 닫는 괄호면 여는 괄호를 만날 때까지 모두 pop
                    while operator and operator[-1] != '(':
                        postfix.append(operator.pop())
                    if operator: 
                        operator.pop() # '(' 제거
                else:
                    # 현재 연산자(x)의 우선순위가 스택 최상단(operator[-1])의 우선순위보다 
                    # 작거나 같으면, 스택에서 꺼내서 postfix에 넣음
                    while operator and prec[operator[-1]] >= prec[x]:
                        postfix.append(operator.pop())
                    operator.append(x)

        # 1. 반복문이 끝난 후 남아있는 숫자 처리
        if temp:
            postfix.append(float(temp))

        # 2. 스택에 남아있는 모든 연산자 처리
        while operator:
            postfix.append(operator.pop())

        calc = []
        while postfix:
            token = postfix.popleft()
    
            if isinstance(token, float):
                calc.append(token)
            else:
                # 스택 구조상 뒤에 있는 숫자(오른쪽 피연산자)가 먼저 pop됩니다.
                num_b = calc.pop()
                num_a = calc.pop()
                
                result = cal(num_a, num_b, token)
                calc.append(result)
        
        embed_result = build_simple_embed(
            title="계산기",
            description=f"🔢 계산 결과"
        )
        embed_result.add_field(name = "입력한 식", value = msg.replace('*', '\\*'), inline = False)
        embed_result.add_field(name = "계산된 값", value = f"{calc[0]:.2f}")

        # 2. send_message의 embed 인자에 전달
        await interaction.response.send_message(embed=embed_result, ephemeral=True)

#########################################################################################################
        
    @app_commands.command(name="시간", description="현재 시간 및 UTC 시간을 알려줍니다") # 시간 260616
    async def clock(self, interaction: discord.Interaction):
        now=time.time()
        utc=int(now%(24*3600))//3600
        hour=(utc+9)%24
        min=int(now%(24*3600))//60%60
        sec=int(now%(24*3600))%60

        hour_emoji = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔',
                      '🕕', '🕖', '🕗', '🕘', '🕙', '🕙']
        embed_result = build_simple_embed(
            title="시간",
            description=f"{hour_emoji[hour%12]} 현재 시간"
        )

        embed_result.add_field(name="UTC 기준", value= f"{utc:02d}:{min:02d}:{sec:02d}", inline= False)
        embed_result.add_field(name="UTC 기준", value= f"{hour:02d}:{min:02d}:{sec:02d}", inline= False)

        await interaction.response.send_message(embed=embed_result, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="가위바위보", description="루이나와 가위바위보를 합니다.") # 가위바위보 260616
    @app_commands.choices(
        player=[
            app_commands.Choice(name="✌️ 가위", value="scissors"),
            app_commands.Choice(name="👊 바위", value="rock"),
            app_commands.Choice(name="✋ 보", value="paper")
        ]
    )
    async def RSP(self, interaction: discord.Interaction, player: app_commands.Choice[str]):
        rsp_url={"scissors" : "https://i.imgur.com/Y7MOdGP.jpg", "rock" : "https://i.imgur.com/acrBIVe.jpg", "paper" : "https://i.imgur.com/II1ClVF.jpg"} # 가 바 보
        computer=random.choice(["scissors","rock","paper"])

        embed_result = build_simple_embed(
            title="가위바위보",
            description="🎲 게임 결과"
        )

        if player == computer: # Player Draw
            embed_result.set_image(url=rsp_url[computer])
            embed_result.add_field(name="비김!",value="Luina가 낸 것 : {0}".format(computer),inline=False)
        else:
            if (player == "scissors" and computer == "paper") or (player == "rock" and computer == "scissors") or (player == "paper" and computer == "rock"): # Player Win
                embed_result.set_image(url=rsp_url[computer])
                embed_result.add_field(name="이김!",value=f"Luina가 낸 것 : {computer}", inline=False)
            else: # Player Lose
                embed_result.set_image(url=rsp_url[computer])
                embed_result.add_field(name="짐!",value=f"Luina가 낸 것 : {computer}", inline=False)
        
        await interaction.response.send_message(embed=embed_result, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="소라고동", description="소라고동님이 정답을 알려줍니다.") # 소라고동 201102 / 260616
    @app_commands.describe(msg="무엇을 물어볼까요?")
    async def conch_shell(self, interaction: discord.Interaction, msg: str):
        if msg == None:
            await 도움말(ctx, '소라고동')
            return
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(3)

        embed=build_simple_embed(
            title="소라고동",
            description="🐚 소라고동님의 말씀"
        )
        embed.add_field(name=msg, value="그래" if random.randint(0, 1) else "안돼")
        await interaction.followup.send(embed=embed, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="선택", description="최대 10개 중 한 개를 골라줍니다.") # 소라고동 ??? / 240313 / 260616
    @app_commands.describe(tp1 ="최소 2개정도는 입력해야 합니다")
    @app_commands.describe(tp2 ="최소 2개정도는 입력해야 합니다")
    async def choice(self, interaction: discord.Interaction,
                     tp1: str, tp2: str, tp3: Optional[str] = None,
                    tp4: Optional[str] = None, tp5: Optional[str] = None, tp6: Optional[str] = None,
                    tp7: Optional[str] = None, tp8: Optional[str] = None, tp9: Optional[str] = None, tp10: Optional[str] = None):
        
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(1.5)

        topics = [val for key, val in locals().items() if "tp" in key and val is not None]
        topic = random.choice(topics)
        len_emoji = {2 : "2️⃣", 3 : "3️⃣", 4 : "4️⃣", 5 : "5️⃣", 6 : "6️⃣",
                     7 : "7️⃣", 8 : "8️⃣", 9 : "9️⃣", 10 : "0️⃣",}

        embed=build_simple_embed(
            title="선택",
            description=f"{len_emoji[len(topics)]} {len(topics)}개 중에 하나는?"
        )
        embed.add_field(name="결과", value=topic)
        await interaction.followup.send(embed=embed, ephemeral=True)

#########################################################################################################



async def setup(bot):
    await bot.add_cog(General(bot))