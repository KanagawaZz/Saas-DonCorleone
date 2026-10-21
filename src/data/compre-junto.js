/**
 * Sugestões Rápidas de "Compre Junto" no Carrinho - Don Corleone
 *
 * Focado em aumento de ticket médio e comodidade para o cliente:
 * - Bebidas geladas para acompanhar as pizzas e esfihas
 * - Sobremesas artesanais (Pizzas Broto doces e Esfihas doces)
 *
 * Todos os valores são reais e adicionados com 1 clique ao carrinho.
 * Os dados ficam em compre-junto.json, que também é importado pelo backend
 * (import_legacy_data) para que o servidor conheça estes preços.
 */

import itensCompreJunto from './compre-junto.json';

export const ITENS_COMPRE_JUNTO = itensCompreJunto;
