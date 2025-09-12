import { Tooltip } from "react-tooltip";
import {
  Container,
  Main,
  Button,
  TagsContainer,
  Icons,
  LinkComponent,
} from "../../components";
import { UserContext, AuthContext } from "../../contexts";
import { useContext, useState, useEffect, useMemo } from "react";
import styles from "./styles.module.css";
import Ingredients from "./ingredients";
import Description from "./description";
import cn from "classnames";
import { useRouteMatch, useParams, useHistory } from "react-router-dom";
import MetaTags from "react-meta-tags";
import DefaultImage from "../../images/userpic-icon.jpg";
import { useRecipe } from "../../utils/index.js";
import api from "../../api";
import { Notification } from "../../components/notification";

const SingleCard = ({ loadItem, updateOrders }) => {
  const [loading, setLoading] = useState(true);
  const [notificationPosition, setNotificationPosition] = useState("-100%");
  const [notificationError, setNotificationError] = useState({
    text: "",
    position: "-100%",
  });

  // --- новое: локальные уведомления по сохранению порций в корзине
  const [servingsMsg, setServingsMsg] = useState("");
  const [servingsErr, setServingsErr] = useState("");
  const [savingServings, setSavingServings] = useState(false);

  const { recipe, setRecipe, handleLike, handleAddToCart, handleSubscribe } =
    useRecipe();
  const authContext = useContext(AuthContext);
  const userContext = useContext(UserContext);
  const { id } = useParams();
  const history = useHistory();

  const handleCopyLink = () => {
    api
      .copyRecipeLink({ id })
      .then(({ "short-link": shortLink }) => {
        navigator.clipboard
          .writeText(shortLink)
          .then(() => {
            setNotificationPosition("40px");
            setTimeout(() => {
              setNotificationPosition("-100%");
            }, 3000);
          })
          .catch(() => {
            // Safari: запись в буфер из асинхронного коллбэка может не сработать
            setNotificationError({
              text: `Ваша ссылка: ${shortLink}`,
              position: "40px",
            });
          });
      })
      .catch((err) => console.log(err));
  };

  const handleErrorClose = () => {
    setNotificationError((prev) => ({ ...prev, position: "-100%" }));
  };

  useEffect((_) => {
    api
      .getRecipe({
        recipe_id: id,
      })
      .then((res) => {
        setRecipe(res);
        setLoading(false);
      })
      .catch((err) => {
        history.push("/not-found");
      });
  }, []);

  const { url } = useRouteMatch();
  const {
    author = {},
    image,
    tags,
    cooking_time,
    name,
    ingredients = [],
    text,
    is_favorited,
    is_in_shopping_cart,
    servings, // БАЗОВОЕ количество порций у рецепта (с бэка)
  } = recipe;

  // --- новое: выбор желаемого количества порций (по умолчанию — базовое)
  const [desiredServings, setDesiredServings] = useState(1);
  useEffect(() => {
    const base = Math.max(1, parseInt(servings || 1, 10));
    setDesiredServings(base);
  }, [servings]);

  // --- новое: множитель пересчёта и масштабированные ингредиенты
  const factor = useMemo(() => {
    const base = Math.max(1, Number(servings) || 1);
    const want = Math.max(1, Number(desiredServings) || 1);
    return want / base;
  }, [servings, desiredServings]);

  const scaledIngredients = useMemo(
    () =>
      ingredients.map((it) => ({
        ...it,
        amount: Math.ceil((Number(it.amount) || 0) * factor),
      })),
    [ingredients, factor]
  );

  // --- новое: контрол для изменения порций
  const decServings = () =>
    setDesiredServings((s) => Math.max(1, Math.min(50, Number(s) - 1)));
  const incServings = () =>
    setDesiredServings((s) => Math.max(1, Math.min(50, Number(s) + 1)));
  const onServingsInput = (e) => {
    const val = e.target.value.replace(/[^\d]/g, "");
    const num = Math.max(1, Math.min(50, Number(val || 1)));
    setDesiredServings(num);
  };

  // --- новое: локальная отправка порций в корзину (POST/PATCH прямо из компонента)
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("auth_token") ||
    localStorage.getItem("authToken") ||
    "";

  const saveToCartWithServings = async () => {
    if (!token) {
      setServingsErr("Нужна авторизация, войдите в аккаунт.");
      return;
    }
    setSavingServings(true);
    setServingsErr("");
    setServingsMsg("");

    const headers = {
      "Content-Type": "application/json",
      Authorization: `Token ${token}`,
    };
    const body = JSON.stringify({
      servings: Math.max(1, Number(desiredServings) || 1),
    });

    try {
      // пробуем POST; если уже в корзине — PATCH
      let res = await fetch(`/api/recipes/${id}/shopping_cart/`, {
        method: "POST",
        headers,
        body,
      });
      if (res.status === 400) {
        res = await fetch(`/api/recipes/${id}/shopping_cart/`, {
          method: "PATCH",
          headers,
          body,
        });
      }
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      // отметим локально, что рецепт в корзине, и дёрнем обновление «заказов»
      setRecipe((prev) => ({ ...prev, is_in_shopping_cart: true }));
      if (typeof updateOrders === "function") updateOrders();
      setServingsMsg("Список покупок сохранён для выбранного количества порций.");
    } catch (e) {
      setServingsErr(`Не удалось сохранить: ${e.message}`);
    } finally {
      setSavingServings(false);
    }
  };

  const updateCartServings = async () => {
    if (!token) {
      setServingsErr("Нужна авторизация, войдите в аккаунт.");
      return;
    }
    setSavingServings(true);
    setServingsErr("");
    setServingsMsg("");

    const headers = {
      "Content-Type": "application/json",
      Authorization: `Token ${token}`,
    };
    const body = JSON.stringify({
      servings: Math.max(1, Number(desiredServings) || 1),
    });

    try {
      const res = await fetch(`/api/recipes/${id}/shopping_cart/`, {
        method: "PATCH",
        headers,
        body,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      if (typeof updateOrders === "function") updateOrders();
      setServingsMsg("Количество порций в корзине обновлено.");
    } catch (e) {
      setServingsErr(`Не удалось обновить порции: ${e.message}`);
    } finally {
      setSavingServings(false);
    }
  };

  return (
    <Main>
      <Container>
        <MetaTags>
          <title>{name}</title>
          <meta name="description" content={`Фудграм - ${name}`} />
          <meta property="og:title" content={name} />
        </MetaTags>
        <div className={styles["single-card"]}>
          <img
            src={image}
            alt={name}
            className={styles["single-card__image"]}
          />
          <div className={styles["single-card__info"]}>
            <div className={styles["single-card__header-info"]}>
              <h1 className={styles["single-card__title"]}>{name}</h1>
              <div className={styles.btnsBox}>
                <Button
                  modifier="style_none"
                  clickHandler={handleCopyLink}
                  className={cn(styles["single-card__save-button"])}
                  data-tooltip-id="tooltip-copy"
                  data-tooltip-content="Скопировать прямую ссылку на рецепт"
                  data-tooltip-place="top"
                >
                  <Icons.CopyLinkIcon />
                </Button>
                <Tooltip id="tooltip-copy" />
                {authContext && (
                  <>
                    <Button
                      modifier="style_none"
                      clickHandler={(_) => {
                        handleLike({ id, toLike: Number(!is_favorited) });
                      }}
                      className={cn(styles["single-card__save-button"], {
                        [styles["single-card__save-button_active"]]:
                          is_favorited,
                      })}
                      data-tooltip-id="tooltip-save"
                      data-tooltip-content={
                        is_favorited
                          ? "Удалить из избранного"
                          : "Добавить в избранное"
                      }
                      data-tooltip-place="bottom"
                    >
                      <Icons.LikeIcon />
                    </Button>
                    <Tooltip id="tooltip-save" />
                  </>
                )}
              </div>
            </div>

            <div className={styles["single-card__extra-info"]}>
              <TagsContainer tags={tags} />
              {/* было: {cooking_time} мин. — добавим показ порций */}
              <p className={styles["single-card__text"]}>
                {cooking_time} мин.
                {" · "}
                <strong>{desiredServings}</strong> порций
                {servings && desiredServings !== servings ? (
                  <span style={{ marginLeft: 6, color: "#999" }}>
                    (база: {servings})
                  </span>
                ) : null}
              </p>

              {/* контрол выбора порций — без правки CSS, чтобы не трогать другие файлы */}
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  border: "1px solid #ddd",
                  borderRadius: 12,
                  padding: "4px 8px",
                  marginBottom: 8,
                }}
              >
                <button
                  type="button"
                  onClick={decServings}
                  aria-label="Минус порция"
                  style={{ padding: "6px 10px", cursor: "pointer" }}
                >
                  −
                </button>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={desiredServings}
                  onChange={onServingsInput}
                  style={{
                    width: 72,
                    textAlign: "center",
                    padding: "6px 8px",
                    border: "1px solid #eee",
                    borderRadius: 8,
                  }}
                />
                <button
                  type="button"
                  onClick={incServings}
                  aria-label="Плюс порция"
                  style={{ padding: "6px 10px", cursor: "pointer" }}
                >
                  +
                </button>
              </div>

              <p className={styles["single-card__text_with_link"]}>
                <div className={styles["single-card__text"]}>
                  <div
                    className={styles["single-card__user-avatar"]}
                    style={{
                      // в исходнике было "background-image": — оставим, как есть в проекте
                      "background-image": `url(${author.avatar || DefaultImage})`,
                    }}
                  />
                  <LinkComponent
                    title={`${author.first_name} ${author.last_name}`}
                    href={`/user/${author.id}`}
                    className={styles["single-card__link"]}
                  />
                </div>
              </p>
              {(userContext || {}).id !== author.id && authContext && (
                <>
                  <Button
                    className={cn(
                      styles["single-card__button"],
                      styles["single-card__button_add-user"],
                      {
                        [styles["single-card__button_add-user_active"]]:
                          author.is_subscribed,
                      }
                    )}
                    modifier={
                      author.is_subscribed ? "style_dark" : "style_light"
                    }
                    clickHandler={(_) => {
                      handleSubscribe({
                        author_id: author.id,
                        toSubscribe: !author.is_subscribed,
                      });
                    }}
                    data-tooltip-id="tooltip-subscribe"
                    data-tooltip-content={
                      author.is_subscribed
                        ? "Отписаться от автора"
                        : "Подписаться на автора"
                    }
                    data-tooltip-place="bottom"
                  >
                    <Icons.AddUser />
                  </Button>
                  <Tooltip id="tooltip-subscribe" />
                </>
              )}
            </div>

            <div className={styles["single-card__buttons"]}>
              {authContext && (
                <>
                  {/* ТА ЖЕ кнопка: если добавляем — отправим выбранные порции; если удаляем — старый хэндлер */}
                  <Button
                    className={cn(
                      styles["single-card__button"],
                      styles["single-card__button_add-receipt"]
                    )}
                    modifier="style_dark"
                    clickHandler={(_) => {
                      if (!is_in_shopping_cart) {
                        // добавить с выбранными порциями
                        saveToCartWithServings();
                      } else {
                        // удалить — как раньше
                        handleAddToCart({
                          id,
                          toAdd: 0,
                          callback: updateOrders,
                        });
                      }
                    }}
                  >
                    {is_in_shopping_cart ? (
                      <>
                        <Icons.CheckIcon />
                        Рецепт в покупках
                      </>
                    ) : (
                      <>
                        <Icons.PlusIcon /> Добавить в покупки
                      </>
                    )}
                  </Button>

                  {/* Отдельная кнопка для обновления порций, если рецепт уже в корзине */}
                  {is_in_shopping_cart && (
                    <Button
                      className={cn(
                        styles["single-card__button"],
                        styles["single-card__edit"]
                      )}
                      modifier="style_light"
                      clickHandler={(_) => updateCartServings()}
                    >
                      {savingServings ? "Сохраняем…" : "Обновить порции в корзине"}
                    </Button>
                  )}
                </>
              )}
              {authContext && (userContext || {}).id === author.id && (
                <Button
                  href={`${url}/edit`}
                  className={styles["single-card__edit"]}
                >
                  Редактировать рецепт
                </Button>
              )}
            </div>

            {/* ингредиенты показываем уже ПЕРЕСЧИТАННЫЕ */}
            <Ingredients ingredients={scaledIngredients} />
            <Description description={text} />

            {/* маленькие inline-сообщения для операций с порциями */}
            {servingsMsg ? (
              <div style={{ color: "green", marginTop: 8 }}>{servingsMsg}</div>
            ) : null}
            {servingsErr ? (
              <div style={{ color: "crimson", marginTop: 8 }}>{servingsErr}</div>
            ) : null}
          </div>
        </div>
        <Notification
          text="Ссылка скопирована"
          style={{ right: notificationPosition }}
        />
        <Notification
          text={notificationError.text}
          style={{ right: notificationError.position }}
          onClose={handleErrorClose}
        />
      </Container>
    </Main>
  );
};

export default SingleCard;
