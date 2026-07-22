from app.models import Product, ProductView


def recommended_products(user, limit=6):
    if not user.is_authenticated:
        return (
            Product.query.filter_by(product_status="selling")
            .order_by(Product.created_at.desc())
            .limit(limit)
            .all()
        )
    recent_views = (
        ProductView.query.join(Product)
        .filter(ProductView.user_id == user.user_id)
        .order_by(ProductView.viewed_at.desc())
        .limit(5)
        .all()
    )
    categories = [view.product.category for view in recent_views]
    query = Product.query.filter(
        Product.product_status == "selling",
        Product.seller_id != user.user_id,
    )
    if categories:
        query = query.filter(Product.category.in_(categories))
    return (
        query.order_by(Product.view_count.desc(), Product.created_at.desc())
        .limit(limit)
        .all()
    )
