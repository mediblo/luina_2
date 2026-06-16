import discord
from discord.ext import commands
from discord import app_commands

from collections import deque
import time
import random

from utils.embed_builder import build_simple_embed

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        await interaction.edit_original_response(content=None, embed=embed)

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
        await interaction.response.send_message(embed=embed_result)
        
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

        await interaction.response.send_message(embed=embed_result)

    @app_commands.command(name="가위바위보", description="루이나와 가위바위보를 합니다.") #가위바위보 260616
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

async def setup(bot):
    await bot.add_cog(General(bot))