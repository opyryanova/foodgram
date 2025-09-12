import styles from "./style.module.css";
import { Tooltip } from "react-tooltip";
import { LinkComponent, Icons, Button, TagsContainer, Popup } from "../index";
import { AuthContext } from "../../contexts";
import { useContext, useState } from "react";
import cn from "classnames";
import DefaultImage from "../../images/userpic-icon.jpg";

const Card = ({
  name = "Без названия",
  id,
  image,
  is_favorited,
  is_in_shopping_cart,
  tags,
  cooking_time,
  servings,
  author = {},
  handleLike,
  handleAddToCart,
  updateOrders,
}) => {
  const authContext = useContext(AuthContext);
  const [toLogin, setToLogin] = useState(false);
  const [whiteSpaceWrap, setWhiteSpaceWrap] = useState(false);

  return (
    <div className={styles.card}>
      <div className={styles.card__header}>
        <TagsContainer tags={tags} className={styles.card__tags} />
        <LinkComponent href={`/recipes/${id}`} title="Перейти к рецепту">
          <div className={styles.card__image}>
            <img src={image} alt={name} />
          </div>
        </LinkComponent>
      </div>
      <div className={styles.card__body}>
        <LinkComponent href={`/recipes/${id}`} title={name}>
          <h3
            className={cn(styles.card__title, {
              [styles.card__title_wrap]: whiteSpaceWrap,
            })}
            onMouseEnter={() => setWhiteSpaceWrap(true)}
            onMouseLeave={() => setWhiteSpaceWrap(false)}
          >
            {name}
          </h3>
        </LinkComponent>

        <div className={styles.card__row}>
          <div className={styles.card__author}>
            <div className={styles.card__autorpic}>
              <img src={author.avatar || DefaultImage} alt="userpic" />
            </div>
            <LinkComponent
              href={`/user/${author.id}`}
              title={`${author.first_name} ${author.last_name}`}
              className={styles.card__link}
            />
          </div>
          <div className={styles.card__time}>{cooking_time} мин. · {(servings || 1)} порций</div>
        </div>
        <div className={styles.card__controls}>
          <Button
            className={styles.card__add}
            click
            onClick={() => {
              if (!authContext.isAuth) {
                setToLogin(true);
                return;
              }
              handleAddToCart({
                id,
                toAdd: Number(!is_in_shopping_cart),
                callback: updateOrders,
              });
            }}
          >
            {is_in_shopping_cart ? (
              <>
                <Icons.CheckIcon />
                Рецепт добавлен
              </>
            ) : (
              <>
                <Icons.PlusIcon />
                Добавить в покупки
              </>
            )}
          </Button>

          <Button
            className={cn(styles.card__like, {
              [styles.card__like_active]: is_favorited,
            })}
            click
            onClick={() => {
              if (!authContext.isAuth) {
                setToLogin(true);
                return;
              }
              handleLike({ id, toLike: !is_favorited });
            }}
            data-tooltip-id={id.toString()}
            data-tooltip-content={
              is_favorited ? "Удалить из избранного" : "Добавить в избранное"
            }
            data-tooltip-place="bottom"
          >
            <Icons.LikeIcon />
          </Button>
          <Tooltip id={id.toString()} />
        </div>
      </div>

      {toLogin && (
        <Popup close={() => setToLogin(false)}>
          <div style={{ padding: 24 }}>
            <p style={{ marginBottom: 12 }}>
              Необходимо войти в аккаунт, чтобы выполнить действие.
            </p>
            <div style={{ display: "flex", gap: 12 }}>
              <LinkComponent href="/auth/signin" className="button">
                Войти
              </LinkComponent>
              <LinkComponent href="/auth/signup" className="button button_outline">
                Регистрация
              </LinkComponent>
            </div>
          </div>
        </Popup>
      )}
    </div>
  );
};

export default Card;
