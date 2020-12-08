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
        self.session = requests.Session()
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
            pagination_block = soup.find('div',{'class':'ems-sdk-grid-paginator__page-buttons'})
            if not pagination_block:
                raise Exception('pagination error')
            right_pagination_index = pagination_block.find_all('div',{'class':'ems-sdk-grid-paginator__page-button'})
            pagination_limit = right_pagination_index[4].get_text()
            print('Counted pages', pagination_limit,'...')
        return int(pagination_limit)

    def get_offer_date(self, url):
        #узнаем даты действия акции и записываем url обложки для дальнейшей выгрузки
        r = self.session.get(url)
        soup = bs4.BeautifulSoup(r.text,'lxml')
        offer_info = soup.find('span',{
        'class':'psw-p-l-xs psw-body-2 psw-text-medium psw-c-secondary psw-m-x-3xs psw-m-y-4xs'}).text
        offer_date = datetime.datetime.strptime(offer_info.split(' ')[2], '%d/%m/%Y').date()
        return offer_info, offer_date

    def parse_game(self, item):
        #ищем игры со скидками
        sale = item.find('div',{'class':'discount-badge__container psw-l-anchor'})
        if sale is not None:
            title = item.find('noscript',{'class':'psw-layer'}).find('img').get('alt')
            price_block = item.find('div',{'class':'price__container'})
            if not price_block:
                print(title, 'something wrong in price block')
                return None
            sale_price_block = price_block.find('span',{'class':'price'})
            if not sale_price_block:
                print(title, 'something wrong in sale price block')
                return None
            sale_price = int(sale_price_block.get_text().strip('RUB').replace('.',''))
            regular_price_block = price_block.find('strike',{'class':'price price--strikethrough psw-m-l-xs'})
            if not regular_price_block:
                print(title, 'something wrong in regular price block')
                return None
            regular_price = int(regular_price_block.get_text().strip('RUB').replace('.',''))
            url_id = item.find('a').get('href')
            url = 'https://store.playstation.com' + url_id
            images_block = item.find('div',{'class':'ems-sdk-product-tile-image__container'})
            images_refs = images_block.find('span',{'class':'psw-media-frame psw-fill-x psw-image psw-aspect-1-1'})
            image = images_refs.find('img',{'class':'psw-top-left psw-l-fit-cover'}).get('src')
            return Game(
            title = title,
            sale_price = sale_price,
            regular_price = regular_price,
            sale = sale.text,
            url = url,
            image = image)

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
        return games_container

    def sale_alert(self):
        #проходим по собранным в массив играм в поиске нужной нам информации касательно сроков распродажи
        try:
            games_data = self.parse_all()
            for game in games_data:
                sales_info = self.get_offer_date(game[4])
                sales = sales_info[0]
                text = game[0] + '\n' + str(game[1]) + ' руб. ' + '(прежняя цена ' + str(game[2]) + ' руб.)' + '\n' + game[3] + '\n' + game[4] + '\n' + sales
                print(game[5])
                print(text)
                tb = telebot.TeleBot('Your bot token')
                tb.send_photo('@Channel_ID', game[5], caption = text)
                print('send')
        except Exception as e:
            if e.args[0] == ('pagination error'):
                print('something wrong in pagination block')
                return
        print('Done')

def main():
    s = PS_Parser()
    s.sale_alert()
if __name__ == '__main__':
    main()
