# build_files.sh

echo "BUILD START"
pip install -r requirements.txt

echo "Make migration"
python3.9 manage.py makemigrations --noinput 
python3.9 manage.py migrate --noinput 

python3.9 manage.py collectstatic --noinput --clear
echo "BUILD END"
