import os,sys,tempfile,secrets,multiprocessing as mp
from pathlib import Path
from datetime import timedelta
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
out=root/'screenshots'
roles='seller node partner drive fleet atlas wild'.split()
names=['Артем','Настя','Настя','Валерий','Валерий','Андрей','Светлана']
def setup(db,role):
    os.environ.update(DJANGO_SETTINGS_MODULE='settings',WB_SERVICE=role)
    import settings
    settings.DATABASES['default']['NAME']=db
    import django
    django.setup()
def serve(db,role,pipe):
    setup(db,role)
    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import make_server,WSGIRequestHandler
    from django.utils import timezone
    from datetime import datetime
    timezone.now=lambda:datetime.fromisoformat(Path(db+'.time').read_text())
    class Quiet(WSGIRequestHandler):
        def log_message(self,*args): pass
    with make_server('127.0.0.1',0,get_wsgi_application(),handler_class=Quiet) as server:
        pipe.send(server.server_port)
        server.serve_forever()
def capture(folder):
    db=str(Path(folder)/'gallery.sqlite3')
    setup(db,'seller')
    from django.core.management import call_command
    from django.utils import timezone
    from django.contrib.auth.models import User,Group
    from ledger.models import Node,Packaging,Trip,Tariff,Vehicle
    from playwright.sync_api import sync_playwright,expect
    now=timezone.now().replace(minute=0,second=0,microsecond=0)
    clock=Path(db+'.time')
    clock.write_text(now.isoformat())
    call_command('migrate',verbosity=0)
    pw=secrets.token_urlsafe(18)
    users={}
    for role,name in zip(roles,names):
        u=User.objects.filter(username=name).first() or User.objects.create_user(name,password=pw)
        u.groups.add(Group.objects.get(name=role))
        users[role]=u
    nodes=[]
    for city,address,cap,peak,hub in [('Москва','Москва · Электрозаводская, 21',670,413,False),('Чебоксары','Чебоксары · Ярмарочная, 8',330,241,False),('Казань','Казань · Чистопольская, 61',490,287,False),('Нижний Новгород','РЦ Нижний Новгород · Московское шоссе',3200,1635,True)]:
        n=Node.objects.create(city=city,name=address,capacity=cap,peak=peak,hub=hub,owner=users['partner'])
        n.workers.add(users['node']);nodes.append(n)
    pack=Packaging.objects.create(name='Гофрокороб для книг, двухслойный',k=1,stacking=0)
    for i,(a,b,h,end,price) in enumerate([(0,1,2,15,218),(1,2,16,19,94),(0,3,3,11,265),(3,2,13,21,198)]):
        car=Vehicle.objects.create(fleet=users['fleet'],plate=['А714МС77','В683ТР21','К492ОХ52','Н215МК16'][i],litres=8500,kg=1250)
        car.drivers.add(users['drive'])
        Trip.objects.create(vehicle=car,driver=users['drive'],origin=nodes[a],destination=nodes[b],departure=now+timedelta(hours=h),arrival=now+timedelta(hours=end),logistic=price)
    Tariff.objects.create(start=now-timedelta(days=12),a=1,b=.35,rub=1,handling=13,risk=4)
    procs=[];urls={};out.mkdir(exist_ok=True)
    try:
        for role in roles:
            r,w=mp.Pipe(False);proc=mp.Process(target=serve,args=(db,role,w));proc.start();procs.append(proc)
            urls[role]='http://127.0.0.1:'+str(r.recv())
        with sync_playwright() as api:
            browser=api.chromium.launch(channel='chrome',headless=True)
            pages={}
            def shot(p,name,area=None):
                p.mouse.move(2,2)
                if area:area.screenshot(path=out/(name+'.png'))
                else:
                    p.evaluate('window.scrollTo(0,0)')
                    p.screenshot(path=out/(name+'.png'),full_page=True)
            def click(p,label):
                with p.expect_response(lambda r:r.url.endswith('/api/') and r.request.method=='POST') as response:
                    p.get_by_role('button',name=label,exact=True).click()
                assert response.value.ok,response.value.text()
                p.wait_for_load_state('networkidle')
            for role in roles:
                p=browser.new_page(viewport={'width':1440,'height':960},locale='ru-RU',timezone_id='Europe/Moscow');pages[role]=p
                if role=='seller':
                    p.goto(urls[role]+'/register/');shot(p,'01-registration')
                p.goto(urls[role]+'/login/')
                p.locator('[name=username]').fill(users[role].username)
                p.locator('[name=password]').fill(pw)
                if role=='seller':shot(p,'02-login')
                p.get_by_role('button',name='Войти').click()
                p.wait_for_load_state('networkidle')
                expect(p.locator('header')).to_contain_text(users[role].username)
            for role,file in [('partner','03-node-capacity'),('fleet','04-fleet-schedule'),('wild','05-tariffs')]:shot(pages[role],file)
            p=pages['atlas'];f=p.locator('section').filter(has=p.get_by_role('heading',name='Распределить партию'))
            for key,value in [('stockМосква',37),('stockЧебоксары',18),('needsВладимир',19),('needsКазань',23),('needsЙошкар-Ола',13)]:
                f.locator('[name="'+key+'"]').fill(str(value))
            f.locator('[name=mode]').select_option('simplex')
            shot(p,'06-atlas-input',f)
            for mode,idx in [('simplex','07'),('ai','08')]:
                f.locator('[name=mode]').select_option(mode);click(p,'Распределить партию')
                expect(p.get_by_role('heading',name='План перевозок',exact=False)).to_be_visible()
                p.evaluate('window.scrollTo(0,0)');p.screenshot(path=out/(idx+'-atlas-'+mode+'.png'))
            p=pages['seller']
            for k,v in [('reference','КП-2611-047'),('product','Атласы Поволжья в твёрдом переплёте, 6 экземпляров'),('length','38'),('width','29'),('height','22'),('kg','7.4'),('days','2'),('deadline',(timezone.localtime(now)+timedelta(hours=36)).strftime('%Y-%m-%dT%H:%M'))]:
                p.locator('[name='+k+']').fill(v)
            for k,v in [('origin',nodes[0].pk),('destination',nodes[2].pk),('packaging',pack.pk)]:p.locator('[name='+k+']').select_option(str(v))
            shot(p,'09-seller-parcel')
            click(p,'Рассчитать');shot(p,'10-route-via-cheboksary')
            partner=pages['partner']
            partner.locator('[name=node]').select_option(str(nodes[1].pk));partner.locator('input[name=peak]').last.fill('316')
            click(partner,'Применить' if partner.get_by_role('button',name='Применить').count() else 'Изменить внешнюю загрузку')
            shot(partner,'11-peak-at-transit-node')
            click(p,'Рассчитать');expect(p.locator('section h2').first).to_contain_text('РЦ Нижний Новгород')
            shot(p,'12-rerouted-via-hub')
            click(p,'Оформить отправление');shot(p,'13-booked')
            node=pages['node'];driver=pages['drive']
            def refresh(page):page.reload(wait_until='networkidle')
            def step(page,prefix):
                button=page.get_by_role('button',name=prefix,exact=False).first
                click(page,button.inner_text())
            refresh(node);shot(node,'14-node-intake');step(node,'Принять')
            for i,h in enumerate([3,13]):
                clock.write_text((now+timedelta(hours=h)).isoformat());refresh(driver);step(driver,'Забрать')
                if not i:shot(driver,'15-driver-in-transit')
                clock.write_text((now+timedelta(hours=[11,21][i])).isoformat());step(driver,'Передать')
            refresh(node);shot(node,'16-node-handover');step(node,'Выдать')
            refresh(p);expect(p.get_by_role('cell',name='Выдан')).to_be_visible();shot(p,'17-order-complete')
            browser.close()
    finally:
        for proc in procs:proc.terminate();proc.join()
        from django.db import connections
        connections.close_all()
if __name__=='__main__':
    with tempfile.TemporaryDirectory() as folder:capture(folder)