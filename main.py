precisa so ajustar esse código apenas para a coluna "% dos pedidos" ficarem no formato de porcentagem. Só isso, não mude logica de nada e não altere mais nada e mande o código completo respeitando as identações

 # ============================
    # 8) "Compram junto" (Market Basket por pedido)
    # ============================
    st.subheader("🧠 Compram junto (combos mais frequentes)")

    pedido_skus = (
        df_cli[[col_pedido, col_sku]]
        .dropna()
        .astype(str)
        .groupby(col_pedido)[col_sku]
        .apply(lambda x: sorted(set([i.strip() for i in x.tolist() if i.strip()])))
    )

    if pedido_skus.shape[0] < 3:
        st.info("Poucos pedidos no período para calcular combinações com confiança.")
    else:
        from itertools import combinations

        pares = {}
        for skus in pedido_skus:
            if len(skus) < 2:
                continue
            for a, b in combinations(skus, 2):
                key = tuple(sorted((a, b)))
                pares[key] = pares.get(key, 0) + 1

        if not pares:
            st.info("Não foi possível gerar pares (pedidos com 2+ SKUs).")
        else:
            df_pares = (
                pd.DataFrame([{"SKU_A": k[0], "SKU_B": k[1], "Frequência": v} for k, v in pares.items()])
                .sort_values("Frequência", ascending=False)
                .reset_index(drop=True)
            )
            df_pares["% dos pedidos"] = (df_pares["Frequência"] / pedido_skus.shape[0] * 100).round(1)

            sku_ancora = st.selectbox(
                "Ver combinações a partir do SKU:",
                ["(Mostrar todos)"] + sorted(df_cli[col_sku].dropna().astype(str).unique().tolist()),
                key="sku_ancora_pairs",
            )

            df_view_pares = df_pares.copy()
            if sku_ancora != "(Mostrar todos)":
                df_view_pares = df_view_pares[
                    (df_view_pares["SKU_A"] == sku_ancora) | (df_view_pares["SKU_B"] == sku_ancora)
                ].copy()

                df_view_pares["Sugestão"] = df_view_pares.apply(
                    lambda r: r["SKU_B"] if r["SKU_A"] == sku_ancora else r["SKU_A"], axis=1
                )

            st.dataframe(df_view_pares.head(30), use_container_width=True, hide_index=True)

    st.markdown("---")
