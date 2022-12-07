s27: attack_sanscrypt.py
	time python attack_sanscrypt.py -f=final-synth.v -t s27

clean:
	$(RM) *.v *.png key.txt
	$(RM) -r generated

