export PYTHONPATH=${PYTHONPATH}:/users/bryan/projects/treasure_raider/app/apps

cd /users/Bryan/projects/pyramid/pyramid/loaders
appcfg.py upload_data --url=http://localhost:8080/remote_api --has_header --email=twistedogre@gmail.com --config_file=character_loader.py --filename=fake_characters.csv --kind=main_character /users/bryan/projects/pyramid
