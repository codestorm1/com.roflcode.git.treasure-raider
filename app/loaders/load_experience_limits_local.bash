cd /users/Bryan/projects/treasure_raider/app/apps/treasure_raider/loaders


export PYTHONPATH=${PYTHONPATH}:/users/bryan/projects/treasure_raider/app/apps

tr '\r' '\n' < experience_limits.csv > el.csv
appcfg.py upload_data --url=http://localhost:8080/remote_api --has_header --email=twistedogre@gmail.com --config_file=experience_limit_loader.py --filename=el.csv --kind=Experience_limits /users/bryan/projects/treasure_raider/app
rm el.csv
