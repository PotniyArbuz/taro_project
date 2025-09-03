// Месячный прогноз
// Функция для плавной прокрутки (оставляем без изменений)
function smoothScrollTo(target, duration = 1000) {
    const start = window.scrollY;
    let targetPosition;

    if (target instanceof HTMLElement) {
        targetPosition = target.getBoundingClientRect().top + start - 50;
    } else {
        targetPosition = document.documentElement.scrollHeight - window.innerHeight;
    }

    const distance = targetPosition - start;
    let startTime = null;

    function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const progress = Math.min(timeElapsed / duration, 1);
        const ease = easeInOutQuad(progress);

        window.scrollTo(0, start + distance * ease);

        if (timeElapsed < duration) {
            requestAnimationFrame(animation);
        }
    }

    function easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }

    requestAnimationFrame(animation);
}

// Функция для получения оставшихся запросов
async function fetchRemainingRequests(userId) {
    try {
        const response = await fetch('https://ai-girls.ru/remaining-requests', {
            method: 'GET',
            headers: {
                'X-Telegram-User-Id': userId
            }
        });

        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        const data = await response.json();
        const remaining = data.remaining;
        document.getElementById("remaining-requests").innerText = `(осталось запросов: ${remaining})`;
    } catch (error) {
        console.error('Ошибка получения оставшихся запросов:', error);
        document.getElementById("remaining-requests").innerText = ``;
    }
}

// Функция для отправки запроса в YandexGPT (оставляем без изменений)
async function getYandexGPTResponse(question, selectedCards, userId) {
    try {
        const response = await fetch('https://ai-girls.ru/yandex-gpt', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': userId
            },
            body: JSON.stringify({ question, cards: selectedCards, user_id: userId, chat_id: chatId, source: "month" })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || `Ошибка HTTP: ${response.status}`);
        }

        const data = await response.json();
        return data.response || 'Не удалось получить ответ.';
    } catch (error) {
        console.error('Ошибка прокси:', error);
        return error.message || 'Не удалось получить ответ. Проверьте подключение или повторите попытку.';
    }
}


// Функция для отображения надписи "Спасибо 😊"
function showThanksMessage() {
    const thanksMessage = document.getElementById("thanks-message");
    thanksMessage.style.display = "block";
    thanksMessage.style.opacity = "1";

    // Скрываем через 2 секунды
    setTimeout(() => {
        thanksMessage.style.opacity = "0";
        setTimeout(() => {
            thanksMessage.style.display = "none";
        }, 500); // Ждём завершения затухания
    }, 2000);
}

// Функция для проверки состояния кнопки
function updateButtonState() {
    const questionInput = document.getElementById("name").value;
    const startBtn = document.getElementById("start-btn");
    startBtn.disabled = !questionInput.trim();
}

document.getElementById("name").addEventListener("input", updateButtonState);
document.getElementById("thank-btn").addEventListener("click", showThanksMessage);

// Инициализация при загрузке страницы
document.addEventListener("DOMContentLoaded", () => {
    const user = window.Telegram.WebApp.initDataUnsafe.user || {};
    const userId = user.id || "unknown";
    fetchRemainingRequests(userId); // Получаем количество оставшихся запросов
});


// Функция для запуска расклада (с обновлением для 7 карт)
async function startReading() {
    const name = document.getElementById("name").value.trim();
    const age = document.getElementById("age").value.trim();
    const additionalInfo = document.getElementById("additional-info").value.trim();
    const question = `Информация о человеке:\nИмя: ${name}\nВозраст: ${age}\nДополнительная информация: ${additionalInfo}\n` + 
    "Расклад “Месячный прогноз” (7 карт)\n" +
    "1 карта - Общая энергия месяца — какое настроение и атмосфера будут сопровождать тебя в течение месяца, какой будет общий эмоциональный и событийный фон.\n" +
    "2 карта - Главное событие месяца — ключевое событие или поворотный момент, который окажет наибольшее влияние на твою жизнь.\n" +
    "3 карта - Финансы и работа — что ждёт в профессиональной сфере: возможности, риски и потенциал роста.\n" +
    "4 карта - Личная жизнь и отношения — как будут развиваться романтические и/или семейные отношения, новые знакомства или внутренние перемены.\n" +
    "5 карта - Здоровье и энергия — на что обратить внимание в физическом и эмоциональном состоянии, как поддерживать ресурсность.\n" +
    "6 карта - Возможности и дары месяца — неожиданные шансы, удачные стечения обстоятельств, скрытые плюсы периода. \n" +
    "7 карта - Совет Таро - как лучше всего прожить этот месяц: что усилить, что отпустить, на что направить фокус." +
    "Ответ должен быть максимально развернутым. Количество слов в ответе должно быть не менее 1200.";

    const user = window.Telegram.WebApp.initDataUnsafe.user || {};
    const userId = user.id || "unknown";

    // Скрываем предыдущий ответ и кнопку "Спасибо"
    const answerDiv = document.getElementById("answer");
    answerDiv.style.display = "none";
    document.getElementById("answer-text").innerText = "";
    const thankBtn = document.getElementById("thank-btn");
    thankBtn.style.display = "none";

    // Показываем анимацию
    const animationDiv = document.getElementById("animation");
    animationDiv.style.display = "block";
    animationDiv.innerHTML = '<div id="deck" class="deck"><img src="images/deck1.jpg" alt="Колода карт" style="width: 100%; height: 100%;"></div>';

    // Выбираем 7 случайных карт
    const selectedCards = [];
    while (selectedCards.length < 7) {
        const randomIndex = Math.floor(Math.random() * cards.length);
        const card = cards[randomIndex];
        if (!selectedCards.includes(card)) {
            selectedCards.push(card);
        }
    }
    
    // Запускаем запрос к YandexGPT заранее и сохраняем промис
    const gptPromise = getYandexGPTResponse(question, selectedCards, userId);

    // Настройка размеров и позиций карт для анимации
    const screenWidth = window.innerWidth;
    const baseCardWidth = screenWidth < 600 ? screenWidth / 3 - 20 : 120;
    const gap = 10;
    const cardWidth = baseCardWidth + gap;

    // Первый ряд: 2 карты
    const totalWidthFirstRow = baseCardWidth * 2 + gap;
    let startLeftFirstRow = (screenWidth - totalWidthFirstRow) / 2;
    if (startLeftFirstRow < 10) startLeftFirstRow = 10;
    // Второй ряд: 3 карты
    const totalWidthSecondRow = baseCardWidth * 3 + gap * 2;
    let startLeftSecondRow = (screenWidth - totalWidthSecondRow) / 2;
    if (startLeftSecondRow < 10) startLeftSecondRow = 10;
    // Третий ряд: 2 карты
    const totalWidthThirdRow = baseCardWidth * 2 + gap;
    let startLeftThirdRow = (screenWidth - totalWidthThirdRow) / 2;
    if (startLeftThirdRow < 10) startLeftThirdRow = 10;

    const deck = document.getElementById("deck");
    deck.style.width = `${baseCardWidth}px`;
    const deckHeight = baseCardWidth * 1.5;

    const deckTop = 50;
    const firstRowTop = deckTop + deckHeight + deckHeight / 2;
    const secondRowTop = firstRowTop + deckHeight + gap;
    const thirdRowTop = secondRowTop + deckHeight + gap;

    const cardElements = [];

    selectedCards.forEach((card, index) => {
        const cardElem = document.createElement("div");
        cardElem.classList.add("card");
        cardElem.style.width = `${baseCardWidth}px`;
        cardElem.style.height = `${baseCardWidth * 1.5}px`;

        const cardInner = document.createElement("div");
        cardInner.classList.add("card-inner");

        const cardBack = document.createElement("div");
        cardBack.classList.add("card-back");
        const backImg = document.createElement("img");
        backImg.src = "images/deck1.jpg";
        backImg.alt = "Задняя сторона карты";
        cardBack.appendChild(backImg);

        const cardFront = document.createElement("div");
        cardFront.classList.add("card-front");
        const frontImg = document.createElement("img");
        frontImg.src = `images/${card}.jpg`;
        frontImg.alt = card;
        cardFront.appendChild(frontImg);

        cardInner.appendChild(cardBack);
        cardInner.appendChild(cardFront);
        cardElem.appendChild(cardInner);

        // Распределяем карты по рядам
        if (index < 2) {
            // Первый ряд: 2 карты
            cardElem.style.left = `${startLeftFirstRow + (index * cardWidth)}px`;
            cardElem.style.top = `${firstRowTop}px`;
        } else if (index < 5) {
            // Второй ряд: 3 карты (индексы 2, 3, 4)
            cardElem.style.left = `${startLeftSecondRow + ((index - 2) * cardWidth)}px`;
            cardElem.style.top = `${secondRowTop}px`;
        } else {
            // Третий ряд: 2 карты (индексы 5, 6)
            cardElem.style.left = `${startLeftThirdRow + ((index - 5) * cardWidth)}px`;
            cardElem.style.top = `${thirdRowTop}px`;
        }

        cardElem.style.animation = `spread-out 2s ease-in-out forwards ${index * 0.5}s`;
        animationDiv.appendChild(cardElem);
        cardElements.push(cardElem);
    });

    // Определяем время завершения анимации
    const lastSpreadOutTime = 2000 + (selectedCards.length - 1) * 500;

    cardElements.forEach((cardElem, index) => {
        setTimeout(() => {
            cardElem.classList.add("flipped");
        }, lastSpreadOutTime + index * 500);
    });

    answerDiv.style.display = "block";
    document.getElementById("answer-text").innerText = ``;
    animationDiv.style.minHeight = `${thirdRowTop + deckHeight + 20}px`;
    smoothScrollTo(answerDiv, 6000);

    // Для ожидания
    const loadingDiv = document.getElementById("loading");
    
    // Показываем индикатор загрузки с меняющимися фразами через 9000 мс
    setTimeout(() => {
        loadingDiv.style.display = "block"; // Показываем индикатор после переворота карт

        // Массив фраз для смены
        const loadingMessages = [
            "Получаем ответ на ваш запрос...",
            "Анализируем выпавшие карты...",
            "Формируем предсказание...",
            "Смотрим в будущее для вас..."
        ];
        let messageIndex = 0;
        const loadingText = document.getElementById("loading-text");

        // Устанавливаем первую фразу сразу
        loadingText.innerText = loadingMessages[messageIndex];

        // Запускаем смену текста каждые 3 секунды
        const textInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % loadingMessages.length; // Циклический переход по массиву
            loadingText.innerText = loadingMessages[messageIndex];
        }, 3000);

        // Сохраняем textInterval в глобальной области видимости, чтобы можно было остановить его позже
        window.loadingTextInterval = textInterval;
    }, 9000);

    // После окончания анимации получаем ответ из ранее отправленного запроса
    setTimeout(async () => {
        
        const gptResponse = await gptPromise;
        // Скрываем индикатор загрузки
        loadingDiv.style.display = "none";
        // Останавливаем смену текста, если интервал был запущен
        if (window.loadingTextInterval) {
            clearInterval(window.loadingTextInterval);
        }
        const formattedGptResponse = gptResponse.replace(/\n/g, '<br>');
        const boldedResponse = formattedGptResponse.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        const cleanedResponse = boldedResponse.replace(/\*/g, '');
        const cleanedResponse1 = cleanedResponse.replace(/#/g, '');

        const answerText = `
            <strong style="font-size: 20px;">Выпавшие карты:</strong><br><br>
            1) ${selectedCards[0]}<br>
            2) ${selectedCards[1]}<br>
            3) ${selectedCards[2]}<br>
            4) ${selectedCards[3]}<br>
            5) ${selectedCards[4]}<br>
            6) ${selectedCards[5]}<br>
            7) ${selectedCards[6]}<br>
            <hr class="divider">
            <strong style="font-size: 20px;">Ответ на расклад с учетом выпавших карт:</strong><br><br>
            ${cleanedResponse1}
        `;
        answerDiv.classList.add("show");
        document.getElementById("answer-text").innerHTML = answerText;
        thankBtn.style.display = "block";  // Показываем кнопку после получения ответа
        smoothScrollTo(answerDiv, 3000);

        // Обновляем количество оставшихся запросов после выполнения расклада
        fetchRemainingRequests(userId);
    }, 100);
}

document.getElementById("start-btn").addEventListener("click", startReading);



if (typeof Telegram !== "undefined" && Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
}