import datetime
import bs4
import requests
from collections import namedtuple
import telebot

#создаем кортеж для хранения всей необходимой информации по каждой игре
InnerBlock = namedtuple('Block', 'title, sale_price, regular_price, sale, url, image')

class Game(InnerBlock):

#создаем класс для хранения информации по играм
    def __str__(self):
        return f'{self.title}\n{self.sale_price}\n{self.regular_price}\n{self.sale}\n{self.url}\n{self.image}'

class PS_Parser:

    def __init__(self):
        #инициализируем класс с параметрами для отправки GET запросов
        self.session =  requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0',
             'Accept-Language' :'ru', }

    def get_page(self, page):
        #получаем HTML страницы через GET запрос
        url = 'https://store.playstation.com/ru-ru/category/44d8bb20-653e-431e-8ad0-c0a365f68d2f/' + str(page)
        r = self.session.get(url)
        return r.text

    def get_pagination_limit(self):
        #считаем общее количество страниц
        start_page = '0'
        pagination_limit = '1'
        while pagination_limit != start_page:
            start_page = pagination_limit
            text = self.get_page(start_page)
            soup = bs4.BeautifulSoup(text, 'lxml')
            pagination_limit = soup.find('div',{'class':'ems-sdk-grid-paginator__page-buttons'}
            ).find_all('div',{'class':'ems-sdk-grid-paginator__page-button'})[4].get_text()
            print('Counted pages', pagination_limit,'...')
        return int(pagination_limit)

    def get_offer_date(self, url):
        #узнаем даты действия акции и записываем url обложки для дальнейшей выгрузки
        r = self.session.get(url)
        soup = bs4.BeautifulSoup(r.text,'lxml')
        offer_info = soup.find('span',{
        'class':'psw-p-l-xs psw-body-2 psw-text-medium psw-c-secondary psw-m-x-3xs psw-m-y-4xs'}).text
        offer_date = datetime.datetime.strptime(offer_info.split(' ')[2], '%d/%m/%Y').date()
        #image_url = soup.find('noscript',{'class':'psw-layer'}).find('img').get('src')
        return offer_info, offer_date#, image_url

    def parse_game(self, item):
        #ищем игры со скидками
        try:
            sale = item.find('div',{'class':'discount-badge__container psw-l-anchor'})
            if sale is not None:
                title = item.find('noscript',{'class':'psw-layer'}
                ).find('img').get('alt')
                sale_price = int(item.find(
                'div',{'class':'price__container'}
                ).find('span',{'class':'price'}
                ).get_text().strip('RUB').replace('.',''))
                regular_price = int(item.find('div',{'class':'price__container'}
                ).find('strike',{'class':'price price--strikethrough'}
                ).get_text().strip('RUB').replace('.',''))
                url = 'https://store.playstation.com' + item.find('a').get('href')
                image = item.find('div',{'class':'ems-sdk-product-tile-image__container'}
                ).find('span',{'class':'psw-media-frame psw-fill-x psw-image psw-aspect-1-1'}
                ).find('img',{'class':'psw-top-left psw-l-fit-cover'}).get('src')
                return Game(
                title = title,
                sale_price = sale_price,
                regular_price = regular_price,
                sale = sale.text,
                url = url,
                image = image)
        except:
            TypeError

    def get_games(self, page: int = None):
        #собираем все контейнеры с играми из одной странички
        text = self.get_page(page=page)
        soup = bs4.BeautifulSoup(text,'lxml')
        container = soup.find_all('div',{'class':'ems-sdk-product-tile'})
        return container



    def parse_all(self):
        #собираем все игры со скидками в один массив
        limit = self.get_pagination_limit()
        games_container = []
        for i in range(1, limit+1):
            print('Parsing page', i)
            container = self.get_games(page = i)
            for item in container:
                game_data = self.parse_game(item)
                if game_data is not None:
                    games_container.append(game_data)
        return  games_container

    def sale_alert(self):
        #проходим по собранным в массив играм в поиске нужной нам информации касательно сроков распродажи
        games_data = self.parse_all()
        for game in games_data:
            try:
                sales_info = self.get_offer_date(game[4])
                sales = sales_info[0]
                text = game[0] + '\n' + str(game[1]) + ' руб. ' + '(прежняя цена ' + str(game[2]) + ' руб.)' + '\n' + game[3] + '\n' + game[4] + '\n' + sales_info[0]
                print(game[5])
                print(text)
                tb = telebot.TeleBot('Your bot token')
                tb.send_photo('@Channel_ID', game[5], caption = text)
                print('send')
            except:
                TypeError
        print('Done')

def main():
    s = PS_Parser()
    s.sale_alert()
if __name__ == '__main__':
    main()
