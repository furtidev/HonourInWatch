import sqlite3
import os
import disnake
from disnake import Option, OptionType
from disnake.ext import commands
from decouple import config, UndefinedValueError
import time
import datetime
from keep_alive import keep_alive


try:
	tokens = {
		'discord': config('DISCORD_API_TOKEN', cast=str),
	}
except UndefinedValueError:
	exit()

# manager role

lock_roles = {
    'manager': 'InWatch'
}


# connect to SQLite3

db = sqlite3.connect('main.db')

# the SQLite cursor.

explorer = db.cursor()

# jailer lmao

jailer = 445958910344560641


# The primary bot class.
class Bot(commands.Bot):
	def __init__(self):
		super().__init__(
			command_prefix='>>', 
			intents=disnake.Intents.all(), 
			help_command=None, 
			strip_after_prefix=True, 
			case_insensitive=True
		)
		
	async def on_connect(self):
		os.system('clear')
		
	async def on_ready(self):
		print('Bot is ready for testing / use!')
		
	async def on_message(self, message: disnake.Message):
		if message.author == self.user:
			return
		
bot = Bot()






# UI 

class TenderOptionsView(disnake.ui.View):
	def __init__(self, row: str, normal_name: str, timeout: int=10):
		super().__init__(timeout=timeout)
		self.normal_name = normal_name
		self.row = row
		self.response = None

	@disnake.ui.button(emoji='⬆️',style=disnake.ButtonStyle.green)
	async def confirm(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
		channel = bot.get_channel(tokens['logs_channel'])
		role_id = 927486150598328340
		if role_id in interaction.author._roles:
			interactor_id = interaction.author.name + "#" + interaction.author.discriminator
			explorer.execute(f'SELECT * FROM tender_shares WHERE contractor_id = "{interactor_id}" AND contract_task = "{self.row}"')
			row_count = explorer.rowcount
			if row_count == 0:
				explorer.execute(f'INSERT INTO tender_shares(contractor_id, contract_task, share) VALUES(%s, %s, %s)', (interactor_id, self.row, 1))
				explorer.execute(f'UPDATE contracts SET contract_remaining = contract_remaining - 1 WHERE contract_name = {self.row}')
				db.commit()
				embed = disnake.Embed(title="New log!", 
					description=f"{interactor_id} took 1x share from the contract -> **{self.normal_name}**",
					color=0x55FF55
					)
				await channel.send(embed=embed)
			else:
				explorer.execute(f'UPDATE tender_shares SET share = share + 1 WHERE contractor_id = "{interactor_id}" AND contract_task = "{self.row}"')
				explorer.execute(f'UPDATE contracts SET contract_remaining = contract_remaining - 1 WHERE contract_name = {self.row}')
				db.commit()
				embed = disnake.Embed(title="New log!", 
					description=f"{interactor_id} took 1x share from the contract -> **{self.normal_name}**",
					color=0x55FF55
					)
				await channel.send(embed=embed)
			await interaction.response.send_message(f"You took 1x of the total tender share of **{self.normal_name}**.", ephemeral=True)
		else:
			await interaction.response.send_message(f"Only Contractors are allowed to join.", ephemeral=True)
	# This one is similar to the confirmation button except sets the inner value to `False`
	@disnake.ui.button(emoji='⬇️', style=disnake.ButtonStyle.red)
	async def cancel(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
		channel = bot.get_channel(tokens['logs_channel'])
		role_id = 927486150598328340
		if role_id in interaction.author._roles:
			interactor_id = str(interaction.author)
			print(interactor_id)
			explorer.execute(f'SELECT * FROM tender_shares WHERE contractor_id = "{interactor_id}" AND contract_task = "{self.row}"')
			row_count = explorer.rowcount
			if row_count == 0:
				await interaction.response.send_message(f"You have less than x1 of the total share. What are you trying to cancel anyway?", ephemeral=True)
				embed = disnake.Embed(title="New log!", 
					description=f"{interactor_id} tried to cancel 1x of their share without having any share in the first place from the contract -> **{self.normal_name}**",
					color=0xFF5555
					)
				await channel.send(embed=embed)
			else:
				explorer.execute(f'UPDATE tender_shares SET share = share - 1 WHERE contractor_id = "{interactor_id}" AND contract_task = "{self.row}"')
				explorer.execute(f'UPDATE contracts SET contract_remaining = contract_remaining + 1 WHERE contract_name = {self.row}')
				db.commit()
				await interaction.response.send_message(f"You cancelled 1x of your total share of **{self.normal_name}**.", ephemeral=True)
				embed = disnake.Embed(title="New log!", 
					description=f"{interactor_id} cancelled 1x of their total share from the contract -> **{self.normal_name}**",
					color=0xFF5555
					)
				await channel.send(embed=embed)
		else:
			await interaction.response.send_message(f"Only Contractors are allowed to join.", ephemeral=True)

	
# The cog for declaring main commands.
class CoreCommands(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.slash_command(
		name='new',
		description='Create a new contract.',
		options = [
			Option("name", "Name of the contract.", OptionType.string, required=True),
			Option("details", "Details of the contract.", OptionType.string, required=True),
			Option("total_share", "Total number of tender share", OptionType.integer, required=True),
			Option("total_time", "Total timeframe of the contract.", OptionType.string, required=True),
			Option("task_name","Lowercase + no spaces. This will help the bot interact with the backend. No job in frontend.", OptionType.string, required=True)
		])
	@commands.has_any_role(lock_roles['manager'])
	async def _new(self, inter: disnake.ApplicationCommandInteraction, name: str, details: str, total_share: int, total_time: str, task_name: str):
		timestamp = int(time.mktime(datetime.datetime.strptime(total_time, "%d/%m/%Y").timetuple()))
		view = TenderOptionsView(task_name, name, (timestamp-int(time.time())))
		explorer.execute("INSERT INTO contracts (contract_name,contract_share,contract_time,contract_remaining) VALUES(%s,%s,%s,%s)", (task_name, total_share, timestamp, total_share))
		db.commit()
		embed = disnake.Embed(
			title=f":mega: New Contract -> {name}", 
			description=f'{details} \n ---- \n Distributed Share: {total_share} \n ---- \n Ends: <t:{int(time.mktime(datetime.datetime.strptime(total_time, "%d/%m/%Y").timetuple()))}:R>'
			)
		await inter.send(embed=embed, view=view)
		await view.wait()

	@commands.slash_command(
		name='stats',
		description='Check contractor stats.',
		)
	async def _stats(self, inter: disnake.ApplicationCommandInteraction):
		explorer.execute("SELECT discord_id, discord_name, points FROM contractors")
		allStats = []
		allList = str()
		for (discord_id, discord_name, points) in explorer:
			allStats.append(":small_blue_diamond: **{}** ({} points)".format(discord_name, format(points, '8,d')))
		for item in allStats:
			allList += f'{item} \n'
		allList = allList.rstrip()
		embed = disnake.Embed(title="Contractor Stats", description=allList)
		await inter.send(embed=embed)

	@commands.slash_command(
		name='reward',
		description='Give points to a specific contractor.',
		options=[
			Option("member", "Mention the server member.", OptionType.user, required=True),
			Option("amount", "Amount of points you want to give them.", OptionType.integer, required=True)
		])
	@commands.has_any_role(lock_roles['manager'])
	async def _reward(self, inter: disnake.ApplicationCommandInteraction, member:str, amount:int):
		explorer.execute(f"UPDATE contractors SET points = points + {amount} WHERE discord_name = '{member}'")
		db.commit()
		embed = disnake.Embed(description=f"**{format(amount, '8,d')}** points has been added to {member}'s account.", color=0x55FF55)
		await inter.send(embed=embed)

		
# Load cogs into the bot.
bot.add_cog(CoreCommands(bot))


# Run the bot.
keep_alive()

bot.run(tokens['discord'])
