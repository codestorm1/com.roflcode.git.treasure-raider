export PYTHONPATH=${PYTHONPATH}:/users/bryan/projects/treasure_raider/app/apps

tr '\r' '\n' < config.csv > cfg.csv
appcfg.py upload_data --url=http://treasure-raider.appspot.com/remote_api --has_header --email=twistedogre@gmail.com --config_file=config_loader.py --filename=cfg.csv --kind=Config /users/bryan/projects/treasure_raider/app
cp cfg.csv config.csv
rm cfg.csv
