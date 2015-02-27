# -*- coding: utf-8 -*-
# 
# Tilastokeskuksen aineistojen visualisointi
#  Piirtää halutut kuvaajat valitusta Tilastokeskuksen .px-tietokannasta
# 
# Tekijät:
#  Heta Rekilä
#  Heli Kallio
#  Ilari Jalli
#  Esko Niinimäki
# 
# Versio 0.9
from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
import pickle
import ordereddict
import json
import parsija2
import tiedostontallennus
import os
import pdb
import pprint
import osoitehakija


# Luo json-muotoisesta POSTilla lähetetystä datasta (formista) listamuotoisen
# version. 
def listaa(otsikot_str, tkanta):
	# tarkistetaan paljonko taulukoita eli otsikkolistoja
	taulukoita = len(tkanta.otsikot)
	# uus hakulista sopivan pituisena
	hakulista = []
	for i in range(taulukoita):
		uusi = []
		hakulista.append(uusi)
	otsikot = otsikot_str[2:-2].split('","')
	# etsitään saaduille alkioille kuuluva listaindeksi ja lisätään alkio
	# sen indeksin kohtaan.
	for otsikko in otsikot:
		for i in range(taulukoita):
			if otsikko in tkanta.otsikot[i]:
				hakulista[i].append(otsikko)
				break
	# muutetaan yhden alkion listat pelkiksi alkion arvoiksi
	for lista in hakulista:
		if isinstance(lista, list):	#aina on 
			if len(lista) == 1: #eli alkioita 1
				i = hakulista.index(lista)
				hakulista[i] = lista[0]
	return hakulista

# Hakee piirrettävien käyrien/palkkien/tms nimen
def hae_hakuotsikot(hakusanat, xakseli, tkanta):
	hakuotsikko_lkm = 0
	hakuotsikkoindeksi = -1
	# nimet poimitaan listamuotoisesta hakuehdosta, joka ei ole x-akseli
	for i in range(len(hakusanat)):
		if isinstance(hakusanat[i], list):
			if i != tkanta.taulukot.index(xakseli):
				hakuotsikko_lkm += 1
				hakuotsikkoindeksi = i
	# jos haluaa piirtää vain yhdestä arvosta, poimitaan ensimmäinen nimeksi
	if hakuotsikkoindeksi == -1:
		if tkanta.taulukot.index(xakseli) == 0:
			hakuotsikkoindeksi = 1
		else:
			hakuotsikkoindeksi = 0
	# jos listamuotoisia hakuehtoja on useampia, hylätään operaatio
	if hakuotsikko_lkm > 1:
		return -1
	return hakuotsikkoindeksi

# Yhdistää haun tuloksen ja arvoyksiköt jsoniksi
def luo_vastaus(yksikot, tulos, minmaks):
	vastaus = {}
	vastaus["yksikot"] = yksikot
	vastaus["tulos"] = tulos
	vastaus["maksimi"] = minmaks["maksimi"]
	vastaus["minimi"] = minmaks["minimi"]
	return json.dumps(vastaus)

# Rekursiivinen maksimiarvon haku listoista
def hae_maksimi(arvolista):
	maksimi = 0
	for alkio in arvolista:
		# voi sisältää alilistoja
		if isinstance(alkio, list):
			maksimi = max(maksimi, hae_maksimi(alkio))
		# arvot pitäisi olla tuplessa
		elif isinstance(alkio, tuple):
			x, y = zip(*arvolista)
			maksimi = max(max(y), maksimi)
			break
		else:
			pass
	return maksimi
	
# Rekursiivinen maksimi- ja minimiarvon haku listoista
def hae_maks_ja_min(arvolista):
	tulos = {}
	tulos["maksimi"] = 1
	tulos["minimi"] = 1
	
	for alkio in arvolista:
		# voi sisältää alilistoja
		if isinstance(alkio, list):
			verrokki = (hae_maks_ja_min(alkio))
			tulos["maksimi"] = max(tulos["maksimi"], verrokki["maksimi"])
			tulos["minimi"] = min(tulos["minimi"], verrokki["minimi"])
		# viimeinen taso
		# arvot pitäisi olla tuplessa
		elif isinstance(alkio, tuple):
			try:
				x, y = zip(*arvolista)
				yy = []
				for arvo in y:
					if arvo != 0 and arvo != 0.0 and not isinstance(arvo, basestring):
						yy.append(arvo)
				tulos["maksimi"] = max(max(yy), tulos["maksimi"])
				tulos["minimi"] = min(min(yy), tulos["minimi"])
				break
			except Exception:
				print "Virhe haettaessa minimiä ja maksimia"
				break
		else:
			pass
	return tulos


def create_app(configfile=None):
	app = Flask(__name__)
						 # https://github.com/mbr/flask-appconfig
	Bootstrap(app)

	# in a real app, these should be configured through Flask-Appconfig
	app.config['SECRET_KEY'] = 'devkey'
	app.config['RECAPTCHA_PUBLIC_KEY'] = \
		'6Lfol9cSAAAAADAkodaYl9wvQCwBMr3qGR_PPHcw'

	# luodaan tietokantaolio ladatun tietokannan varastointiin ja käsittelyyn
	uusi_tkanta = parsija2.Tietokanta()

	@app.route('/')
	def index():
		# poimitaan otsikkotiedoston sisältö
		with open ('otsikot.json' ) as json_data:
			tree4 = json.load( json_data )
			json_data.close() 
		# palautetaan template saadulla tietokantapuulla
		return render_template('tilastopalikka.html',tree = tree4)
			
	# Piirrettävän datan haku
	@app.route('/arvot', methods=['GET', 'POST'])
	def hae_arvot():
		if request.method == 'POST':
			global uusi_tkanta
			# muutetaan hakusanat jatkokäsittelyä varten eri (lista)muotoon
			hakusanat = listaa(request.form['otsikot'], uusi_tkanta)
			# poimitaan x-akseli
			xakseli = request.form['xakseli']
			# haetaan haluttu datajoukko (x-akselin suhteen)
			tuloslista = parsija2.hae_arvoparit(hakusanat, xakseli, uusi_tkanta)
			# haetaan piirrettävien kokonaisuuksien (käyrä/tms) nimet
			minmaks = hae_maks_ja_min(tuloslista)
			haut = hae_hakuotsikot(hakusanat, xakseli, uusi_tkanta)
			if haut < 0:
				return "Tapahtui virhe: Liikaa tai liian vähän hakulistoja"
			# yhdistetään nimet ja data piirtoa varten
			tulos = parsija2.listat_pariksi(hakusanat[haut], tuloslista)
			vastaus = luo_vastaus(uusi_tkanta.yksikot, tulos, minmaks)
			# palautetaan yhdistetty lista jsonina (tekstinä)
			return vastaus
		# ei hyväksytä get-pyyntöä
		else:
			return -1
			
	# Valitun tietokannan lataus, parsinta ja talletus muistiin
	@app.route('/lataus', methods=['GET', 'POST'])
	def hae_hsanat():
		if request.method == 'POST':
			global uusi_tkanta #aiemmin alustettu tietokantaolio
			# poimitaan tietokannan osoite
			nimi = request.form['linkki']
			# ladataan tietokanta levylle
			tied_nimi = tiedostontallennus.Lataa_tiedosto(nimi)
			# parsitaan tietokanta olioon
			uusi_tkanta = parsija2.parsi(tied_nimi)
			# poimitaan hakuotsikot sanakirjaksi
			otsikot_skirja = parsija2.otsikot_sanakirjaksi(uusi_tkanta)
			# poistetaan tietokanta.px levyltä
			os.remove(tied_nimi)
			# palautetaan hakuotsikot jsonina
			return json.dumps(otsikot_skirja)
		# hyväksytään järkevästi vain POST-pyynnöt
		else:
			return "auts"


	@app.route('/puu/')
	def teepuu():
		with open ('otsikot.json' ) as json_data:
		   tree4 = json.load( json_data )
		   json_data.close()
		return render_template('puu_navbar_sis.html', tree = tree4)

   
	@app.route('/palikka2/')
	def palikka2():
		return render_template('tilastopalikka2.html')


	@app.route('/ohje/')
	def ohje():
			return render_template('ohje.html')
    
	return app



if __name__ == '__main__':
	#osoitehakija.hae() #poistettu testikäytön ajaksi
	create_app().run(debug=True)





